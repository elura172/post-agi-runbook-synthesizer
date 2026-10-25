"""Stage 4: Executable Remediation & Rollback Synthesizer.

Grounding: Site Reliability Engineering (Ch 12: Addressing Cascading Failures & Emergency Response).
Generates deterministic shell commands, config patches, explicit rollback operations,
and immediate verification assertions for SRE incident responders.
"""

from __future__ import annotations

from typing import List
from post_agi_runbook_synthesizer.models import FailureDomain, RemediationAction
from post_agi_runbook_synthesizer.pipeline.base import BaseStage, PipelineContext


class RemediationStage(BaseStage):
    """Stage 4: Executable remediation and rollback generation."""

    @property
    def name(self) -> str:
        return "remediation_synthesizer"

    @property
    def s_domain(self) -> str:
        return "Deterministic Mitigation Scripts, Safety Assertions & Rollback Procedures"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        domain = ctx.incident.domain
        model = ctx.incident.target_model
        actions: List[RemediationAction] = []

        if domain == FailureDomain.PROXY_BUFFER_BLOAT:
            actions = [
                RemediationAction(
                    step_number=1,
                    title="Audit Ingress & Reverse Proxy Response Buffering Headers",
                    command=(
                        f"curl -s -D - -o /dev/null -N https://api.openai.com/v1/models "
                        f"-H 'Authorization: Bearer $OPENAI_API_KEY' | grep -iE '(x-accel-buffering|transfer-encoding)'"
                    ),
                    expected_output="transfer-encoding: chunked",
                    rollback_command=None,
                    is_destructive=False,
                    verification_check="Verify that chunked transfer encoding is preserved end-to-end without buffering headers.",
                ),
                RemediationAction(
                    step_number=2,
                    title="Apply Dynamic Nginx / Envoy Streaming Configuration Patch",
                    command=(
                        "cat << 'EOF' > /tmp/stream_proxy_patch.conf\n"
                        "location /v1/chat/completions {\n"
                        "    proxy_buffering off;\n"
                        "    proxy_cache off;\n"
                        "    proxy_read_timeout 300s;\n"
                        "    proxy_set_header X-Accel-Buffering 'no';\n"
                        "}\n"
                        "EOF\n"
                        "sudo cp /tmp/stream_proxy_patch.conf /etc/nginx/conf.d/streaming.conf"
                    ),
                    expected_output="Config written to /etc/nginx/conf.d/streaming.conf",
                    rollback_command="sudo rm -f /etc/nginx/conf.d/streaming.conf && sudo nginx -s reload",
                    is_destructive=False,
                    verification_check="Run `nginx -t` to validate syntax prior to live reload.",
                ),
                RemediationAction(
                    step_number=3,
                    title="Gracefully Reload Reverse Proxy Configuration",
                    command="sudo nginx -s reload || curl -X POST http://127.0.0.1:9901/drain_listeners",
                    expected_output="nginx: configuration file /etc/nginx/nginx.conf test is successful",
                    rollback_command=None,
                    is_destructive=False,
                    verification_check="Verify 0 dropped TCP connections in edge proxy active connection counter.",
                ),
                RemediationAction(
                    step_number=4,
                    title="Verify Chunk Cadence Recovery via Sentinel Streaming Probe",
                    command=(
                        f"sentinel diagnose --model {model} --samples 15 "
                        f"|| python -m post_agi_runbook_synthesizer.cli verify ./test_canary_probe.py"
                    ),
                    expected_output="STREAM_HEALTHY / P95 jitter < 30ms",
                    rollback_command=None,
                    is_destructive=False,
                    verification_check="Assert TTFT < 600ms and inter-chunk jitter P95 < 30ms.",
                ),
            ]

        elif domain == FailureDomain.INFERENCE_SHARD_STALL:
            actions = [
                RemediationAction(
                    step_number=1,
                    title="Query GPU Shard KV-Cache Allocation Pressure",
                    command="curl -s http://routing-mesh.internal:8080/metrics | grep -E 'kv_cache_usage_percent|gpu_memory_used'",
                    expected_output="kv_cache_usage_percent < 85.0",
                    rollback_command=None,
                    is_destructive=False,
                    verification_check="Confirm whether specific shard ID has exhausted paged attention allocation.",
                ),
                RemediationAction(
                    step_number=2,
                    title="Evict Stale Prompt Cache Buckets on Degraded Worker",
                    command="curl -X POST http://routing-mesh.internal:8080/v1/cache/prune -d '{\"older_than_seconds\": 300, \"min_hit_count\": 2}'",
                    expected_output="{\"status\": \"evicted\", \"freed_pages\": 4096}",
                    rollback_command=None,
                    is_destructive=False,
                    verification_check="Verify KV-cache utilization drops below 75% threshold.",
                ),
                RemediationAction(
                    step_number=3,
                    title="Drain and Rolling-Restart Degraded Inference Shard Pod",
                    command="kubectl drain pod-inference-shard-07 --ignore-daemonsets --delete-emptydir-data",
                    expected_output="pod/pod-inference-shard-07 drained",
                    rollback_command="kubectl uncordon pod-inference-shard-07",
                    is_destructive=True,
                    verification_check="Confirm replacement pod reaches READY 1/1 state and rejoins routing mesh.",
                ),
            ]

        elif domain == FailureDomain.RATE_LIMIT_STAMPEDE:
            actions = [
                RemediationAction(
                    step_number=1,
                    title="Inspect Distributed Redis Token Bucket Cluster Health",
                    command="redis-cli -h redis-cluster.internal -p 6379 cluster info | grep -E '(cluster_state|cluster_slots_ok)'",
                    expected_output="cluster_state:ok",
                    rollback_command=None,
                    is_destructive=False,
                    verification_check="Verify 16384/16384 cluster hash slots are assigned and reachable.",
                ),
                RemediationAction(
                    step_number=2,
                    title="Activate Emergency Token Bucket Leak Dampening",
                    command="curl -X POST http://rate-limiter.internal/admin/dampen -d '{\"multiplier\": 1.25, \"window_seconds\": 600}'",
                    expected_output="{\"dampening_active\": true, \"duration\": 600}",
                    rollback_command="curl -X POST http://rate-limiter.internal/admin/dampen -d '{\"multiplier\": 1.0, \"window_seconds\": 0}'",
                    is_destructive=False,
                    verification_check="Ensure 429 error rate across enterprise keys drops below 0.1%.",
                ),
            ]

        else:
            actions = [
                RemediationAction(
                    step_number=1,
                    title="Inspect Service Mesh Ingress Logs",
                    command="journalctl -u ingress-gateway -n 50 --no-pager",
                    expected_output="status 200",
                    rollback_command=None,
                    is_destructive=False,
                    verification_check="Check for 5xx anomalies.",
                )
            ]

        ctx.remediation_actions = actions
        return ctx
