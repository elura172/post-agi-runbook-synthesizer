"""Domain models and data schemas for post-agi-runbook-synthesizer."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    SEV_1 = "SEV-1 (Critical / Outage)"
    SEV_2 = "SEV-2 (Major / Degraded Service)"
    SEV_3 = "SEV-3 (Moderate / Latency Spike)"
    SEV_4 = "SEV-4 (Minor / Cosmetic)"


class FailureDomain(str, Enum):
    PROXY_BUFFER_BLOAT = "PROXY_BUFFER_BLOAT"
    INFERENCE_SHARD_STALL = "INFERENCE_SHARD_STALL"
    RATE_LIMIT_STAMPEDE = "RATE_LIMIT_STAMPEDE"
    KV_CACHE_EVICTION_THRASH = "KV_CACHE_EVICTION_THRASH"
    ROUTING_MESH_SPLIT_BRAIN = "ROUTING_MESH_SPLIT_BRAIN"
    CUSTOM = "CUSTOM"


class TelemetryMetrics(BaseModel):
    ttft_ms: float = Field(default=0.0, description="Time to first token in milliseconds")
    token_cadence_tps: float = Field(default=0.0, description="Tokens per second cadence")
    p95_jitter_ms: float = Field(default=0.0, description="P95 inter-chunk jitter in milliseconds")
    p99_latency_ms: float = Field(default=0.0, description="P99 response latency in milliseconds")
    error_rate: float = Field(default=0.0, description="Observed error rate fraction (0.0 to 1.0)")
    chunks_observed: int = Field(default=0, description="Total chunks observed during sampling")
    prompt_cache_hit: bool = Field(default=False, description="Whether prompt cache was hit")
    status_code: int = Field(default=200, description="HTTP status code")
    raw_samples: List[float] = Field(default_factory=list, description="Raw chunk interval deltas")


class SLIBurn(BaseModel):
    sli_name: str
    target_slo: float
    current_value: float
    burn_rate_1h: float
    budget_exhaustion_hours: Optional[float] = None
    violates_slo: bool = False


class ServiceLayer(str, Enum):
    CLIENT = "Client / SDK Egress"
    ENTERPRISE_EDGE = "Enterprise Edge / WAF Proxy"
    INGRESS_GATEWAY = "Global Anycast Ingress / Envoy"
    ROUTING_MESH = "Model Routing & Scheduling Mesh"
    INFERENCE_WORKER = "Inference Worker (Triton/vLLM Shard)"
    RATE_LIMITER = "Distributed Rate Limiter (Redis Cluster)"
    STATE_STORE = "Persistent State & KV Store"


class ServiceNode(BaseModel):
    id: str
    name: str
    layer: ServiceLayer
    dependencies: List[str] = Field(default_factory=list)
    healthy: bool = True
    degradation_reason: Optional[str] = None


class TopologyModel(BaseModel):
    primary_fault_node: str
    impacted_layer: ServiceLayer
    blast_radius_nodes: List[str] = Field(default_factory=list)
    nodes: Dict[str, ServiceNode] = Field(default_factory=dict)
    invariant_violation: str


class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_requests: int = 3
    backoff_base_ms: float = 200.0
    backoff_max_ms: float = 10000.0
    jitter_strategy: str = "full_decorrelated_jitter"
    circuit_state: str = "HALF_OPEN"
    calculated_delays: List[float] = Field(default_factory=list)


class RemediationAction(BaseModel):
    step_number: int
    title: str
    command: str
    expected_output: str
    rollback_command: Optional[str] = None
    is_destructive: bool = False
    verification_check: str


class CanaryProbeSpec(BaseModel):
    test_name: str
    target_url: str
    http_method: str = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    expected_status_code: int = 200
    max_acceptable_p95_ms: float = 150.0
    max_acceptable_ttft_ms: float = 800.0
    stream_chunk_assertions: List[str] = Field(default_factory=list)


class AlertRule(BaseModel):
    alert_name: str
    expr: str
    duration: str = "2m"
    severity: str = "critical"
    summary: str
    description: str
    runbook_url: Optional[str] = None


class CustomerAdvisory(BaseModel):
    incident_id: str
    status: str
    severity: Severity
    impacted_surface: str
    summary: str
    mitigation_workaround: List[str] = Field(default_factory=list)
    technical_contact_guidance: str


class PostMortemRecord(BaseModel):
    incident_id: str
    timestamp: str
    domain: FailureDomain
    severity: Severity
    theoretical_grounding: str
    root_cause_summary: str
    blast_radius_summary: str
    remediation_summary: str
    recurrence_fingerprint: str
    mttr_seconds: int = 0


class IngestedIncident(BaseModel):
    incident_id: str
    title: str
    target_model: str = "gpt-4o"
    domain: FailureDomain
    severity: Severity
    theoretical_grounding: str = "Distributed Systems Invariants"
    executive_summary: str
    telemetry: TelemetryMetrics = Field(default_factory=TelemetryMetrics)
    whys: List[str] = Field(default_factory=list)
    remediation_notes: List[str] = Field(default_factory=list)
    raw_markdown: Optional[str] = None


class IncidentBundle(BaseModel):
    incident: IngestedIncident
    runbook_md: str
    alerts_yaml: str
    canary_probe_py: str
    customer_advisory_md: str
    postmortem_json: str
    output_dir: str
