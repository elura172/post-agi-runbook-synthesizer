"""Stage 3: Circuit Breaker & Adaptive Damping Policy.

Grounding: RFC 5321 (Backoff Delays), AWS Architecture (Exponential Backoff and Jitter),
Michael Nygard's 'Release It!' (Stability Patterns: Circuit Breaker).
Formulates adaptive circuit trip rules, recovery timeout windows, and decorrelated jitter backoff schedules.
"""

from __future__ import annotations

import random
from post_agi_runbook_synthesizer.models import CircuitBreakerConfig, FailureDomain
from post_agi_runbook_synthesizer.pipeline.base import BaseStage, PipelineContext


class CircuitBreakerStage(BaseStage):
    """Stage 3: Adaptive damping and circuit breaking rules."""

    @property
    def name(self) -> str:
        return "circuit_breaker_damping"

    @property
    def s_domain(self) -> str:
        return "Adaptive Damping, Circuit Tripping & Exponential Backoff with Jitter"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        domain = ctx.incident.domain
        base_ms = 250.0
        max_ms = 8000.0
        failure_threshold = 5
        recovery_seconds = 30.0
        half_open = 3

        if domain == FailureDomain.RATE_LIMIT_STAMPEDE:
            base_ms = 500.0
            max_ms = 30000.0
            failure_threshold = 3
            recovery_seconds = 45.0
            half_open = 2
        elif domain == FailureDomain.INFERENCE_SHARD_STALL:
            base_ms = 1000.0
            max_ms = 15000.0
            failure_threshold = 4
            recovery_seconds = 20.0
            half_open = 5

        # Compute deterministic sample decorrelated jitter progression for 5 retry steps
        # Formula: sleep = min(cap, uniform(base, prev_sleep * 3))
        # Using a deterministic seed based on incident_id for reproducible runbooks
        rng = random.Random(ctx.incident.incident_id)
        delays = []
        current = base_ms
        for _ in range(5):
            sleep_val = min(max_ms, rng.uniform(base_ms, current * 3.0))
            delays.append(round(sleep_val, 1))
            current = sleep_val

        ctx.circuit_breaker = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_seconds,
            half_open_requests=half_open,
            backoff_base_ms=base_ms,
            backoff_max_ms=max_ms,
            jitter_strategy="decorrelated_full_jitter",
            circuit_state="HALF_OPEN",
            calculated_delays=delays,
        )
        return ctx
