"""Stage 1: Telemetry Ingestion & SLI/SLO Pressure Analysis.

Grounding: Google SRE Book (Ch 4: Service Level Objectives), RFC 3393 (IP Packet Delay Variation).
Analyzes streaming metrics (TTFT, inter-chunk jitter, token cadence, error rate)
and determines SLO budget burn rates and degradation thresholds.
"""

from __future__ import annotations

from post_agi_runbook_synthesizer.models import AlertRule, SLIBurn
from post_agi_runbook_synthesizer.pipeline.base import BaseStage, PipelineContext


class TelemetryStage(BaseStage):
    """Stage 1: Telemetry pressure and SLI burn calculation."""

    @property
    def name(self) -> str:
        return "telemetry_pressure_analysis"

    @property
    def s_domain(self) -> str:
        return "SLI/SLO Invariant Analysis & Real-Time Cadence Telemetry"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        metrics = ctx.incident.telemetry
        sli_burns = []
        alerts = []

        # 1. TTFT (Time to First Token) SLI
        # Target: <= 600ms for p95
        ttft_target = 600.0
        ttft_burn = 1.0
        ttft_violates = metrics.ttft_ms > ttft_target
        if ttft_violates:
            ttft_burn = max(1.5, metrics.ttft_ms / ttft_target * 2.0)
            exhaustion = max(0.5, 72.0 / ttft_burn)
        else:
            exhaustion = None

        sli_burns.append(
            SLIBurn(
                sli_name="streaming_ttft_p95_ms",
                target_slo=ttft_target,
                current_value=round(metrics.ttft_ms, 2),
                burn_rate_1h=round(ttft_burn, 2),
                budget_exhaustion_hours=round(exhaustion, 2) if exhaustion else None,
                violates_slo=ttft_violates,
            )
        )

        if ttft_violates:
            alerts.append(
                AlertRule(
                    alert_name="OpenAIStreamingTTFTSLOBreach",
                    expr=f'histogram_quantile(0.95, sum(rate(openai_stream_ttft_seconds_bucket[5m])) by (le, model)) > {ttft_target / 1000.0}',
                    duration="2m",
                    severity="critical" if metrics.ttft_ms > 2000.0 else "warning",
                    summary=f"Streaming TTFT SLI breach on {ctx.incident.target_model}: {metrics.ttft_ms:.1f}ms (target <= {ttft_target}ms)",
                    description="P95 time to first token has breached enterprise SLO, indicating model shard scheduling stall or edge proxy buffering.",
                )
            )

        # 2. Inter-Chunk Jitter SLI
        # Target: <= 30.0ms p95 jitter
        jitter_target = 30.0
        jitter_violates = metrics.p95_jitter_ms > jitter_target
        jitter_burn = (
            max(1.0, metrics.p95_jitter_ms / jitter_target * 2.5)
            if jitter_violates
            else 1.0
        )
        sli_burns.append(
            SLIBurn(
                sli_name="streaming_chunk_jitter_p95_ms",
                target_slo=jitter_target,
                current_value=round(metrics.p95_jitter_ms, 2),
                burn_rate_1h=round(jitter_burn, 2),
                budget_exhaustion_hours=round(max(0.2, 48.0 / jitter_burn), 2)
                if jitter_violates
                else None,
                violates_slo=jitter_violates,
            )
        )

        if jitter_violates:
            alerts.append(
                AlertRule(
                    alert_name="OpenAIStreamChunkJitterAnomaly",
                    expr=f'histogram_quantile(0.95, sum(rate(openai_stream_chunk_inter_arrival_seconds_bucket[5m])) by (le)) > {jitter_target / 1000.0}',
                    duration="3m",
                    severity="critical" if metrics.p95_jitter_ms > 100.0 else "warning",
                    summary=f"Stream chunk inter-arrival jitter exceeds threshold: {metrics.p95_jitter_ms:.1f}ms",
                    description="Severe TCP packet queuing or intermediate reverse proxy response-body buffer bloat observed on SSE stream.",
                )
            )

        # 3. Error Rate SLI
        error_target = 0.01  # 1%
        error_violates = metrics.error_rate > error_target
        error_burn = (
            max(1.0, (metrics.error_rate / error_target) * 5.0)
            if error_violates
            else 1.0
        )
        sli_burns.append(
            SLIBurn(
                sli_name="streaming_http_5xx_error_rate",
                target_slo=error_target,
                current_value=round(metrics.error_rate, 4),
                burn_rate_1h=round(error_burn, 2),
                budget_exhaustion_hours=round(max(0.1, 24.0 / error_burn), 2)
                if error_violates
                else None,
                violates_slo=error_violates,
            )
        )

        if error_violates:
            alerts.append(
                AlertRule(
                    alert_name="OpenAIStreamingHighErrorBudgetBurn",
                    expr="sum(rate(http_requests_total{status=~'5..'}[5m])) / sum(rate(http_requests_total[5m])) > 0.01",
                    duration="1m",
                    severity="critical",
                    summary=f"Streaming HTTP 5xx error budget burn rate at {error_burn:.1f}x",
                    description="High rate of 5xx errors or socket disconnects breaching quarterly error budget in < 24 hours.",
                )
            )

        ctx.sli_burns = sli_burns
        ctx.alerts.extend(alerts)
        return ctx
