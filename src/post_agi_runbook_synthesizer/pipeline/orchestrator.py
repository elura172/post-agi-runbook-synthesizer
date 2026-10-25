"""Stage 8: Unified Runbook Orchestrator & Artifact Compiler.

Grounding: UNIX Composition, Literate DevOps, SRE Production Readiness Standards.
Weaves together telemetry, topology invariants, circuit breaking, deterministic remediation,
adversarial verification, stakeholder comms, and historical continuity into the 5-artifact release bundle.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List
import yaml

from post_agi_runbook_synthesizer.models import IncidentBundle
from post_agi_runbook_synthesizer.pipeline.base import BaseStage, PipelineContext


class OrchestratorStage(BaseStage):
    """Stage 8: Unified runbook and artifact compilation."""

    def __init__(self, output_dir: str = "./artifacts"):
        self.output_dir = output_dir

    @property
    def name(self) -> str:
        return "runbook_orchestrator"

    @property
    def s_domain(self) -> str:
        return "Operational Synthesis, Literate Runbooks & Production Multi-Artifact Bundling"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        incident = ctx.incident
        os.makedirs(self.output_dir, exist_ok=True)

        # 1. Compile Executable Markdown Runbook
        runbook_lines = [
            f"# Operational SRE Runbook: {incident.incident_id}",
            f"> **Failure Domain:** `{incident.domain.value}` | **Severity:** `{incident.severity.value}` | **Target Model:** `{incident.target_model}`",
            f"> **Theoretical Grounding:** {incident.theoretical_grounding}",
            "",
            "## 1. Incident Overview & Blast Radius",
            f"- **Summary:** {incident.executive_summary}",
            f"- **Primary Fault Node:** `{ctx.topology.primary_fault_node if ctx.topology else 'Unknown'}`",
            f"- **Impacted Layer:** `{ctx.topology.impacted_layer.value if ctx.topology else 'Unknown'}`",
            f"- **Blast Radius:** {', '.join(f'`{b}`' for b in (ctx.topology.blast_radius_nodes if ctx.topology else []))}",
            f"- **Invariant Violated:** *{ctx.topology.invariant_violation if ctx.topology else 'None'}*",
            "",
            "## 2. Telemetry & SLI Degradation Profile",
            "| SLI Metric | Target SLO | Observed Value | 1h Burn Rate | Budget Exhaustion | Status |",
            "|---|---|---|---|---|---|",
        ]

        for sli in ctx.sli_burns:
            status = "CRITICAL BREACH" if sli.violates_slo else "NOMINAL"
            exhaustion = f"{sli.budget_exhaustion_hours:.1f}h" if sli.budget_exhaustion_hours else "N/A"
            runbook_lines.append(
                f"| `{sli.sli_name}` | `{sli.target_slo}` | `{sli.current_value}` | `{sli.burn_rate_1h}x` | `{exhaustion}` | **{status}** |"
            )

        runbook_lines.extend(
            [
                "",
                "## 3. Circuit Breaker & Adaptive Damping Policy",
                f"- **Failure Trip Threshold:** `{ctx.circuit_breaker.failure_threshold if ctx.circuit_breaker else 5} consecutive errors`",
                f"- **Recovery Timeout Window:** `{ctx.circuit_breaker.recovery_timeout_seconds if ctx.circuit_breaker else 30.0}s`",
                f"- **Half-Open Concurrency:** `{ctx.circuit_breaker.half_open_requests if ctx.circuit_breaker else 3} probe requests`",
                f"- **Backoff Strategy:** `{ctx.circuit_breaker.jitter_strategy if ctx.circuit_breaker else 'decorrelated_jitter'}`",
                f"- **Sample Retry Backoff Progression (ms):** `{ctx.circuit_breaker.calculated_delays if ctx.circuit_breaker else []}`",
                "",
                "## 4. Executable Remediation Procedures",
            ]
        )

        for step in ctx.remediation_actions:
            destr_badge = " [DESTRUCTIVE ACTION]" if step.is_destructive else ""
            runbook_lines.extend(
                [
                    f"### Step {step.step_number}: {step.title}{destr_badge}",
                    "```bash",
                    step.command,
                    "```",
                    f"- **Expected Output:** `{step.expected_output}`",
                    f"- **Verification Check:** {step.verification_check}",
                ]
            )
            if step.rollback_command:
                runbook_lines.extend(
                    [
                        f"- **Rollback Command:**",
                        "```bash",
                        step.rollback_command,
                        "```",
                    ]
                )
            runbook_lines.append("")

        runbook_lines.extend(
            [
                "## 5. Adversarial Canary Verification",
                "Execute the companion synthetic canary probe to verify system recovery prior to closing the incident:",
                "```bash",
                "pytest -v test_canary_probe.py",
                "```",
                "",
                "## 6. Historical Context & Anti-Recurrence",
                f"- **Recurrence Fingerprint:** `{ctx.ledger_record.recurrence_fingerprint if ctx.ledger_record else 'N/A'}`",
            ]
        )

        if ctx.similar_past_incidents:
            runbook_lines.append("- **Correlated Prior Incidents:**")
            for past in ctx.similar_past_incidents:
                runbook_lines.append(
                    f"  - `{past['incident_id']}` ({past['timestamp']}): {past['root_cause_summary'][:100]}... (MTTR: {past['mttr_seconds']}s)"
                )
        else:
            runbook_lines.append("- No identical prior incidents indexed in local ledger. Baseline record initialized.")

        runbook_lines.append("")
        runbook_md = "\n".join(runbook_lines)

        # 2. Compile Prometheus Alerts YAML
        alerts_dict = {
            "groups": [
                {
                    "name": f"sre_runbook_alerts_{incident.incident_id.lower().replace('-', '_')}",
                    "rules": [
                        {
                            "alert": a.alert_name,
                            "expr": a.expr,
                            "for": a.duration,
                            "labels": {
                                "severity": a.severity,
                                "incident_domain": incident.domain.value.lower(),
                                "model": incident.target_model,
                            },
                            "annotations": {
                                "summary": a.summary,
                                "description": a.description,
                                "runbook_file": "runbook.md",
                            },
                        }
                        for a in ctx.alerts
                    ],
                }
            ]
        }
        alerts_yaml = yaml.dump(alerts_dict, sort_keys=False)

        # 3. Canary Probe Code
        canary_code = ctx.canary_probe_code or "# No canary probe generated"

        # 4. Customer Advisory Markdown
        adv = ctx.customer_advisory
        advisory_md = (
            f"# OpenAI Customer Advisory — {adv.incident_id if adv else incident.incident_id}\n\n"
            f"**Status:** {adv.status if adv else 'Investigating'}  \n"
            f"**Impacted Surface:** {adv.impacted_surface if adv else 'API'}  \n"
            f"**Severity:** {adv.severity.value if adv else incident.severity.value}  \n\n"
            f"### Executive Summary\n"
            f"{adv.summary if adv else incident.executive_summary}\n\n"
            f"### Immediate Actionable Workarounds for Engineering Teams\n"
        )
        if adv:
            for item in adv.mitigation_workaround:
                advisory_md += f"- {item}\n"
            advisory_md += f"\n*{adv.technical_contact_guidance}*\n"

        # 5. Postmortem JSON export
        postmortem_data = {
            "incident_id": incident.incident_id,
            "domain": incident.domain.value,
            "severity": incident.severity.value,
            "target_model": incident.target_model,
            "theoretical_grounding": incident.theoretical_grounding,
            "sli_burns": [s.model_dump() for s in ctx.sli_burns],
            "topology": ctx.topology.model_dump() if ctx.topology else {},
            "circuit_breaker": ctx.circuit_breaker.model_dump() if ctx.circuit_breaker else {},
            "remediation_steps": [r.model_dump() for r in ctx.remediation_actions],
            "recurrence_fingerprint": ctx.ledger_record.recurrence_fingerprint if ctx.ledger_record else "",
        }
        postmortem_json = json.dumps(postmortem_data, indent=2)

        # Write files to output directory
        with open(os.path.join(self.output_dir, "runbook.md"), "w", encoding="utf-8") as f:
            f.write(runbook_md)
        with open(os.path.join(self.output_dir, "alerts.yaml"), "w", encoding="utf-8") as f:
            f.write(alerts_yaml)
        with open(os.path.join(self.output_dir, "test_canary_probe.py"), "w", encoding="utf-8") as f:
            f.write(canary_code)
        with open(os.path.join(self.output_dir, "customer_advisory.md"), "w", encoding="utf-8") as f:
            f.write(advisory_md)
        with open(os.path.join(self.output_dir, "incident_ledger.json"), "w", encoding="utf-8") as f:
            f.write(postmortem_json)

        ctx.runbook_markdown = runbook_md
        ctx.alerts_yaml_content = alerts_yaml

        return ctx

    def compile_bundle(self, ctx: PipelineContext) -> IncidentBundle:
        self.execute(ctx)
        return IncidentBundle(
            incident=ctx.incident,
            runbook_md=ctx.runbook_markdown or "",
            alerts_yaml=ctx.alerts_yaml_content or "",
            canary_probe_py=ctx.canary_probe_code or "",
            customer_advisory_md=ctx.customer_advisory.summary if ctx.customer_advisory else "",
            postmortem_json=json.dumps(ctx.incident.model_dump(), indent=2),
            output_dir=self.output_dir,
        )
