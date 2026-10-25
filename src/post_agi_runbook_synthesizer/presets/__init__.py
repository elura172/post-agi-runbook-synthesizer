"""Preset reference scenarios for OpenAI infrastructure failures."""

from post_agi_runbook_synthesizer.models import (
    FailureDomain,
    IngestedIncident,
    Severity,
    TelemetryMetrics,
)


def get_proxy_buffer_bloat_incident() -> IngestedIncident:
    """Reference Incident 1: SSE Proxy Buffer Bloat."""
    return IngestedIncident(
        incident_id="INC-4FB1577E",
        title="Enterprise Reverse Proxy Buffer Bloat on SSE Stream",
        target_model="gpt-4o",
        domain=FailureDomain.PROXY_BUFFER_BLOAT,
        severity=Severity.SEV_3,
        theoretical_grounding="MIT 6.033 (Computer System Engineering: Network Buffering & The End-to-End Argument)",
        executive_summary=(
            "Severe token inter-arrival jitter detected. Chunks are generated nominally by OpenAI clusters "
            "but are buffered by an intermediate enterprise firewall or reverse proxy before delivering in bursty TCP frames."
        ),
        telemetry=TelemetryMetrics(
            ttft_ms=262.10,
            token_cadence_tps=16.96,
            p95_jitter_ms=125.40,
            chunks_observed=32,
            prompt_cache_hit=False,
            error_rate=0.0,
            raw_samples=[0.015, 0.012, 0.125, 0.130, 0.018, 0.015],
        ),
        whys=[
            "Client reported stuttering streaming animation and UI lag.",
            "Chunk delivery inter-arrival jitter spiked to 125.4ms P95.",
            "Reverse proxy had proxy_buffering turned ON, collecting 4KB chunks before emitting to client.",
        ],
        remediation_notes=[
            "Configure enterprise proxy / WAF to bypass response body buffering for domain api.openai.com.",
            "Set X-Accel-Buffering: no and verify transfer-encoding: chunked passes unbuffered.",
        ],
    )


def get_inference_shard_stall_incident() -> IngestedIncident:
    """Reference Incident 2: Inference Shard Degradation & KV-Cache Eviction Thrash."""
    return IngestedIncident(
        incident_id="INC-9A12E83F",
        title="Model Routing Shard Degradation & Paged Attention Eviction Thrash",
        target_model="o1-preview",
        domain=FailureDomain.INFERENCE_SHARD_STALL,
        severity=Severity.SEV_2,
        theoretical_grounding="MIT 6.824 (Distributed Systems: Memory Sharding, Cache Thrashing & Admission Schedulers)",
        executive_summary=(
            "Model routing mesh shard experienced severe KV-cache allocation pressure under high concurrent reasoning context. "
            "Paged attention block allocation thrashing caused Time to First Token (TTFT) to spike to 14.2 seconds."
        ),
        telemetry=TelemetryMetrics(
            ttft_ms=14200.0,
            token_cadence_tps=7.80,
            p95_jitter_ms=45.20,
            chunks_observed=18,
            prompt_cache_hit=False,
            error_rate=0.08,
            raw_samples=[0.045, 0.050, 0.042, 0.048],
        ),
        whys=[
            "Client experienced 14-second TTFT timeouts on reasoning completions.",
            "Inference GPU worker shard ran out of unfragmented KV paged attention blocks.",
            "Scheduler did not preempt stale low-priority sessions, causing admission queue head-of-line blocking.",
        ],
        remediation_notes=[
            "Prune stale cache buckets and shed speculative decoding on degraded shard.",
            "Perform rolling drain of degraded worker container.",
        ],
    )


def get_rate_limit_stampede_incident() -> IngestedIncident:
    """Reference Incident 3: Distributed Rate-Limit Stampede & Split-Brain."""
    return IngestedIncident(
        incident_id="INC-6C409BD1",
        title="Distributed Token Bucket Replication Partition & 429 Storm",
        target_model="gpt-4o-mini",
        domain=FailureDomain.RATE_LIMIT_STAMPEDE,
        severity=Severity.SEV_1,
        theoretical_grounding="Brewer's CAP Theorem & Lamport Logical Clocks in Partitioned Distributed Counters",
        executive_summary=(
            "Redis cluster partition caused token bucket state desynchronization across ingress gateways. "
            "Legitimate enterprise Tier-5 traffic was subjected to an erroneous 42% HTTP 429 Too Many Requests storm."
        ),
        telemetry=TelemetryMetrics(
            ttft_ms=450.0,
            token_cadence_tps=0.0,
            p95_jitter_ms=10.0,
            chunks_observed=0,
            prompt_cache_hit=False,
            error_rate=0.42,
            status_code=429,
        ),
        whys=[
            "Enterprise accounts received cascading HTTP 429 errors despite remaining well within token quotas.",
            "Replication lag on Redis partition 04 exceeded 2500ms, causing local ingress nodes to assume quota exhaustion.",
            "Client retries without decorrelated jitter created a secondary thundering herd stampede.",
        ],
        remediation_notes=[
            "Failover partition 04 to healthy replica and verify hash slot consistency.",
            "Inject temporary token bucket dampening multiplier to absorb retry surge.",
        ],
    )


PRESETS = {
    "proxy_buffer_bloat": get_proxy_buffer_bloat_incident,
    "inference_shard_stall": get_inference_shard_stall_incident,
    "rate_limit_stampede": get_rate_limit_stampede_incident,
}
