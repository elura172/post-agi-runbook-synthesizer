"""Stage 6: Customer Advisory & Stakeholder Communications.

Grounding: Google SRE Book (Ch 14: Managing Incidents & Emergency Stakeholder Communication).
Generates blameless, SLA-aligned customer statuspage advisories and internal incident command briefs.
"""

from __future__ import annotations

from post_agi_runbook_synthesizer.models import CustomerAdvisory, FailureDomain
from post_agi_runbook_synthesizer.pipeline.base import BaseStage, PipelineContext


class CommsStage(BaseStage):
    """Stage 6: Stakeholder communications synthesizer."""

    @property
    def name(self) -> str:
        return "stakeholder_comms_synthesizer"

    @property
    def s_domain(self) -> str:
        return "Blameless Enterprise Statuspage Advisories & Incident Command Coordination"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        incident = ctx.incident
        domain = incident.domain

        # Generate targeted client workarounds based on failure domain
        workarounds = []
        if domain == FailureDomain.PROXY_BUFFER_BLOAT:
            workarounds = [
                "Configure enterprise egress proxy or WAF (e.g. Nginx, Envoy, Cloudflare, Zscaler) to disable response body buffering for `api.openai.com`.",
                "Ensure client requests include `X-Accel-Buffering: no` and that intermediate hops preserve `Transfer-Encoding: chunked`.",
                "Audit TCP window scaling and MTU settings on enterprise perimeter gateways to prevent packet aggregation.",
            ]
        elif domain == FailureDomain.INFERENCE_SHARD_STALL:
            workarounds = [
                "Clients experiencing elevated TTFT (>5s) should activate client-side request timeouts and implement exponential backoff with full decorrelated jitter.",
                "Where possible, chunk high-context system prompts into reusable prompt-cached prefixes to leverage OpenAI server-side prefix caching.",
            ]
        elif domain == FailureDomain.RATE_LIMIT_STAMPEDE:
            workarounds = [
                "Verify API key usage tiers in the OpenAI Developer Platform dashboard.",
                "Implement distributed client-side rate limit queues (e.g., token bucket or leaky bucket) to smooth burst traffic.",
                "Apply randomized exponential retry backoff on HTTP 429 responses with `Retry-After` header adherence.",
            ]
        else:
            workarounds = [
                "Monitor official status page at https://status.openai.com for real-time resolution updates.",
                "Utilize backup model endpoints or secondary regions where available in your SDK configuration.",
            ]

        advisory = CustomerAdvisory(
            incident_id=incident.incident_id,
            status="Under Investigation / Active Mitigation Applied",
            severity=incident.severity,
            impacted_surface=f"OpenAI API Streaming & Model Inference ({incident.target_model})",
            summary=incident.executive_summary,
            mitigation_workaround=workarounds,
            technical_contact_guidance=(
                "Our Technical Support Engineering team has validated this mitigation. If you require dedicated assistance "
                "verifying proxy bypass rules or tuning SDK retry dynamics, contact support@openai.com referencing this incident ID."
            ),
        )

        internal_brief = (
            f"# Internal Incident Command Brief: {incident.incident_id}\n\n"
            f"- **Target Surface:** `{incident.target_model}`\n"
            f"- **Domain:** `{domain.value}`\n"
            f"- **Severity:** `{incident.severity.value}`\n"
            f"- **Primary Fault Node:** `{ctx.topology.primary_fault_node if ctx.topology else 'Unknown'}`\n"
            f"- **Impacted Layer:** `{ctx.topology.impacted_layer.value if ctx.topology else 'Unknown'}`\n"
            f"- **SLO Burn Rate:** `{ctx.sli_burns[0].burn_rate_1h if ctx.sli_burns else 1.0}x`\n\n"
            f"### Action Plan\n"
            f"1. On-call engineer executing runbook step 1-3.\n"
            f"2. Synthetic canary verification scheduled post-reload.\n"
            f"3. Customer advisory staged for statuspage broadcast.\n"
        )

        ctx.customer_advisory = advisory
        ctx.internal_advisory = internal_brief
        return ctx
