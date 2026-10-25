"""Stage 2: Topology Invariant Model & Blast Radius Analysis.

Grounding: MIT 6.033 (Computer System Engineering: Layering, Modularity, and The End-to-End Argument).
Constructs an explicit dependency graph of the streaming inference topology, isolates the fault layer,
and calculates the blast radius across downstream and upstream nodes.
"""

from __future__ import annotations

from post_agi_runbook_synthesizer.models import (
    FailureDomain,
    ServiceLayer,
    ServiceNode,
    TopologyModel,
)
from post_agi_runbook_synthesizer.pipeline.base import BaseStage, PipelineContext


class TopologyStage(BaseStage):
    """Stage 2: Topology modeling and invariant isolation."""

    @property
    def name(self) -> str:
        return "topology_invariant_analysis"

    @property
    def s_domain(self) -> str:
        return "Distributed Service Graph, Failure Domain Isolation & Blast Radius Analysis"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        domain = ctx.incident.domain

        # Construct reference distributed architecture graph
        nodes = {
            "client_app": ServiceNode(
                id="client_app",
                name="Client SDK / Egress Gateway",
                layer=ServiceLayer.CLIENT,
                dependencies=["edge_proxy"],
                healthy=True,
            ),
            "edge_proxy": ServiceNode(
                id="edge_proxy",
                name="Enterprise WAF / Reverse Proxy (Envoy/Nginx)",
                layer=ServiceLayer.ENTERPRISE_EDGE,
                dependencies=["ingress_gateway"],
                healthy=True,
            ),
            "ingress_gateway": ServiceNode(
                id="ingress_gateway",
                name="Global Anycast Ingress / TLS Termination",
                layer=ServiceLayer.INGRESS_GATEWAY,
                dependencies=["routing_mesh", "rate_limiter"],
                healthy=True,
            ),
            "rate_limiter": ServiceNode(
                id="rate_limiter",
                name="Distributed Token Bucket (Redis Cluster)",
                layer=ServiceLayer.RATE_LIMITER,
                dependencies=[],
                healthy=True,
            ),
            "routing_mesh": ServiceNode(
                id="routing_mesh",
                name="Model Routing & Context Scheduler",
                layer=ServiceLayer.ROUTING_MESH,
                dependencies=["inference_worker"],
                healthy=True,
            ),
            "inference_worker": ServiceNode(
                id="inference_worker",
                name="Inference GPU Shards & Paged Attention KV Cache",
                layer=ServiceLayer.INFERENCE_WORKER,
                dependencies=[],
                healthy=True,
            ),
        }

        # Determine fault isolation and invariant violation based on failure domain
        if domain == FailureDomain.PROXY_BUFFER_BLOAT:
            fault_node = "edge_proxy"
            impacted_layer = ServiceLayer.ENTERPRISE_EDGE
            blast_radius = ["edge_proxy", "client_app"]
            nodes["edge_proxy"].healthy = False
            nodes["edge_proxy"].degradation_reason = (
                "Response body buffering enabled; chunked transfer frames aggregated into bursty TCP packets."
            )
            nodes["client_app"].healthy = False
            nodes["client_app"].degradation_reason = "Client experiencing high jitter and socket read timeouts."
            invariant = "End-to-End Streaming Invariant: Proxy must deliver SSE byte chunks immediately without HTTP response-body buffering (X-Accel-Buffering: no)."

        elif domain == FailureDomain.INFERENCE_SHARD_STALL:
            fault_node = "inference_worker"
            impacted_layer = ServiceLayer.INFERENCE_WORKER
            blast_radius = ["inference_worker", "routing_mesh", "client_app"]
            nodes["inference_worker"].healthy = False
            nodes["inference_worker"].degradation_reason = (
                "KV-cache memory pressure thrashing; scheduler unable to allocate paged attention blocks."
            )
            nodes["routing_mesh"].healthy = False
            nodes["routing_mesh"].degradation_reason = "Health check failures shedding model routing traffic."
            invariant = "Scheduling Invariant: KV-cache eviction latency must not exceed 50ms per token generation batch."

        elif domain == FailureDomain.RATE_LIMIT_STAMPEDE:
            fault_node = "rate_limiter"
            impacted_layer = ServiceLayer.RATE_LIMITER
            blast_radius = ["rate_limiter", "ingress_gateway", "client_app"]
            nodes["rate_limiter"].healthy = False
            nodes["rate_limiter"].degradation_reason = (
                "Redis cluster partition causing token bucket desynchronization and false positive 429 bursts."
            )
            nodes["ingress_gateway"].healthy = False
            nodes["ingress_gateway"].degradation_reason = "Rejecting client requests with HTTP 429 Too Many Requests."
            invariant = "Admission Control Invariant: Token bucket read replication lag must remain under 5ms across active cluster nodes."

        else:
            fault_node = "ingress_gateway"
            impacted_layer = ServiceLayer.INGRESS_GATEWAY
            blast_radius = ["ingress_gateway", "client_app"]
            invariant = "Service Availability Invariant: Ingress must maintain sub-100ms request dispatch."

        ctx.topology = TopologyModel(
            primary_fault_node=fault_node,
            impacted_layer=impacted_layer,
            blast_radius_nodes=blast_radius,
            nodes=nodes,
            invariant_violation=invariant,
        )
        return ctx
