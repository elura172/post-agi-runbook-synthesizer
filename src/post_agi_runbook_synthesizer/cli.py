"""Command-line interface for post-agi-runbook-synthesizer."""

from __future__ import annotations

import argparse
import os
import sys
import pytest
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from post_agi_runbook_synthesizer.parsers.generic_parser import load_incident_from_file
from post_agi_runbook_synthesizer.pipeline import SynthesizerPipeline
from post_agi_runbook_synthesizer.pipeline.postmortem_ledger import (
    DEFAULT_LEDGER_PATH,
    query_historical_incidents,
)
from post_agi_runbook_synthesizer.presets import PRESETS

console = Console()


def handle_synthesize(args: argparse.Namespace) -> int:
    incident_source = args.incident
    # Check if incident is a known preset name
    if incident_source in PRESETS:
        incident = PRESETS[incident_source]()
        console.print(f"[bold cyan]Loaded built-in incident preset:[/bold cyan] `{incident_source}`")
    else:
        if not os.path.exists(incident_source):
            console.print(f"[bold red]Error:[/bold red] Incident file not found: {incident_source}")
            return 1
        incident = load_incident_from_file(incident_source)
        console.print(f"[bold cyan]Parsed incident file:[/bold cyan] `{incident_source}`")

    output_dir = args.output or f"./artifacts/{incident.incident_id}"
    db_path = args.db_path or DEFAULT_LEDGER_PATH

    pipeline = SynthesizerPipeline(output_dir=output_dir, db_path=db_path)
    ctx = pipeline.run(incident)

    # 1. Summary Panel
    console.print(
        Panel.fit(
            f"[bold green]Incident Successfully Synthesized[/bold green]\n"
            f"[bold]ID:[/bold] {incident.incident_id}  |  "
            f"[bold]Domain:[/bold] {incident.domain.value}\n"
            f"[bold]Severity:[/bold] {incident.severity.value}  |  "
            f"[bold]Target Model:[/bold] {incident.target_model}\n"
            f"[bold]Theoretical Grounding:[/bold] {incident.theoretical_grounding}",
            title="SRE Cognitive Pipeline Completed (8 Stages)",
            border_style="green",
        )
    )

    # 2. Telemetry SLI Table
    sli_table = Table(title="SLI Degradation & Error Budget Burn Profile", border_style="blue")
    sli_table.add_column("SLI Metric", style="cyan")
    sli_table.add_column("Target SLO", justify="right")
    sli_table.add_column("Current Observed", justify="right")
    sli_table.add_column("1h Burn Rate", justify="right")
    sli_table.add_column("Budget Exhaustion", justify="right")
    sli_table.add_column("Status", justify="center")

    for sli in ctx.sli_burns:
        status_text = "[bold red]BREACH[/bold red]" if sli.violates_slo else "[green]NOMINAL[/green]"
        exhaustion_str = f"{sli.budget_exhaustion_hours:.1f}h" if sli.budget_exhaustion_hours else "N/A"
        sli_table.add_row(
            sli.sli_name,
            str(sli.target_slo),
            str(sli.current_value),
            f"{sli.burn_rate_1h}x",
            exhaustion_str,
            status_text,
        )
    console.print(sli_table)

    # 3. Topology & Remediation Table
    topo_table = Table(title="Topology Fault Isolation & Remediation Plan", border_style="magenta")
    topo_table.add_column("Fault Node", style="yellow")
    topo_table.add_column("Impacted Layer", style="cyan")
    topo_table.add_column("Blast Radius", style="white")
    topo_table.add_column("Remediation Steps", justify="right")
    topo_table.add_column("Circuit State", style="green")

    topo_table.add_row(
        ctx.topology.primary_fault_node if ctx.topology else "N/A",
        ctx.topology.impacted_layer.value if ctx.topology else "N/A",
        ", ".join(ctx.topology.blast_radius_nodes) if ctx.topology else "N/A",
        str(len(ctx.remediation_actions)),
        ctx.circuit_breaker.circuit_state if ctx.circuit_breaker else "N/A",
    )
    console.print(topo_table)

    # 4. Artifact Bundle Table
    artifact_table = Table(title=f"Compiled SRE Artifact Bundle ({output_dir})", border_style="green")
    artifact_table.add_column("Artifact File", style="bold green")
    artifact_table.add_column("Format", style="cyan")
    artifact_table.add_column("Purpose / Target Audience")

    artifact_table.add_row(
        os.path.join(output_dir, "runbook.md"),
        "Markdown",
        "Executable SRE Runbook with step-by-step triage, commands, and rollbacks",
    )
    artifact_table.add_row(
        os.path.join(output_dir, "alerts.yaml"),
        "YAML",
        "Prometheus Alertmanager rules tuned to incident failure mode",
    )
    artifact_table.add_row(
        os.path.join(output_dir, "test_canary_probe.py"),
        "Python / Pytest",
        "Automated synthetic canary probe and chaos invariant test",
    )
    artifact_table.add_row(
        os.path.join(output_dir, "customer_advisory.md"),
        "Markdown",
        "Blameless enterprise customer advisory & statuspage broadcast",
    )
    artifact_table.add_row(
        os.path.join(output_dir, "incident_ledger.json"),
        "JSON",
        "Persistent post-mortem record indexed into Tezcatl ledger",
    )
    console.print(artifact_table)

    return 0


def handle_verify(args: argparse.Namespace) -> int:
    probe_path = args.probe_path
    if not os.path.exists(probe_path):
        console.print(f"[bold red]Error:[/bold red] Canary probe script not found: {probe_path}")
        return 1

    console.print(Panel(f"Executing Synthetic Canary Verification Suite:\n`{probe_path}`", title="SRE Canary Probe", border_style="cyan"))

    # Clear any previous cached module in sys.modules to prevent pytest import file mismatch
    sys.modules.pop("test_canary_probe", None)
    retcode = pytest.main(["-v", "--import-mode=importlib", "-o", "asyncio_default_fixture_loop_scope=function", probe_path])
    if retcode == 0:
        console.print("[bold green]✔ Canary probe assertions passed: System invariants verified.[/bold green]")
        return 0
    else:
        console.print("[bold red]✘ Canary probe verification failed: Invariant violation detected.[/bold red]")
        return 1


def handle_history(args: argparse.Namespace) -> int:
    db_path = args.db_path or DEFAULT_LEDGER_PATH
    incidents = query_historical_incidents(
        domain=args.domain,
        fingerprint=args.fingerprint,
        limit=args.limit,
        db_path=db_path,
    )

    if not incidents:
        console.print(f"[yellow]No historical incidents found matching query (Ledger: {db_path})[/yellow]")
        return 0

    table = Table(title=f"Historical Post-Mortem Ledger ({db_path})", border_style="cyan")
    table.add_column("Incident ID", style="bold green")
    table.add_column("Timestamp", style="white")
    table.add_column("Domain", style="cyan")
    table.add_column("Severity", style="yellow")
    table.add_column("Root Cause Summary", style="dim")
    table.add_column("MTTR", justify="right")

    for inc in incidents:
        table.add_row(
            inc["incident_id"],
            inc["timestamp"],
            inc["domain"],
            inc["severity"],
            inc["root_cause_summary"][:80] + "...",
            f"{inc['mttr_seconds']}s",
        )
    console.print(table)
    return 0


def handle_audit_architecture(args: argparse.Namespace) -> int:
    incident_source = args.incident
    if incident_source in PRESETS:
        incident = PRESETS[incident_source]()
    else:
        if not os.path.exists(incident_source):
            console.print(f"[bold red]Error:[/bold red] Incident file not found: {incident_source}")
            return 1
        incident = load_incident_from_file(incident_source)

    from post_agi_runbook_synthesizer.diagnostic_lens import evaluate_system_invariants
    from post_agi_runbook_synthesizer.pipeline.topology import TopologyStage
    from post_agi_runbook_synthesizer.pipeline.base import PipelineContext

    # Extract topology
    ctx = TopologyStage().execute(PipelineContext(incident=incident))
    report = evaluate_system_invariants(incident, ctx.topology)

    # Score Panel
    score_color = "green" if report.overall_resilience_score >= 80 else ("yellow" if report.overall_resilience_score >= 60 else "red")
    console.print(
        Panel.fit(
            f"[bold]Target Infrastructure System:[/bold] `{report.system_name}`\n"
            f"[bold]Overall Resilience & Coherence Score:[/bold] [{score_color}]{report.overall_resilience_score}%[/{score_color}]\n"
            f"[dim]{report.synthesis_summary}[/dim]",
            title="Non-Linear Architectural Invariant Audit (The 7 Resonant Gates)",
            border_style=score_color,
        )
    )

    table = Table(title="The 7 Resonant Invariants of Distributed Resilience", border_style="cyan")
    table.add_column("Invariant Dimension", style="bold white")
    table.add_column("Harmonic Root & Domain", style="dim cyan")
    table.add_column("Score", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("System Finding & Architectural Recommendation", style="white")

    for inv in report.invariants:
        c = "green" if inv.score_pct >= 80 else ("yellow" if inv.score_pct >= 60 else "red")
        table.add_row(
            inv.name,
            f"{inv.harmonic_root}\n[dim]{inv.elemental_quality}[/dim]",
            f"[{c}]{inv.score_pct}%[/{c}]",
            f"[{c}]{inv.status}[/{c}]",
            f"{inv.finding}\n[dim]➜ {inv.recommendation}[/dim]",
        )

    console.print(table)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="runbook",
        description="Post-AGI Runbook Synthesizer: Automated SRE incident-to-runbook compiler and alerting synthesizer.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Verb 1: synthesize
    syn_parser = subparsers.add_parser("synthesize", help="Synthesize 5-artifact SRE bundle from incident report or preset")
    syn_parser.add_argument(
        "--incident",
        "-i",
        required=True,
        help="Path to incident file (.md, .json, .yaml) or preset name (proxy_buffer_bloat, inference_shard_stall, rate_limit_stampede)",
    )
    syn_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Target output directory for generated artifacts (default: ./artifacts/<incident_id>)",
    )
    syn_parser.add_argument(
        "--db-path",
        default=None,
        help="Custom SQLite post-mortem ledger path",
    )

    # Verb 2: verify
    ver_parser = subparsers.add_parser("verify", help="Execute synthetic canary probe suite against target system")
    ver_parser.add_argument(
        "probe_path",
        help="Path to test_canary_probe.py file to execute",
    )

    # Verb 3: history
    hist_parser = subparsers.add_parser("history", help="Query historical post-mortem ledger for recurrence patterns")
    hist_parser.add_argument("--domain", "-d", help="Filter by failure domain")
    hist_parser.add_argument("--fingerprint", "-f", help="Filter by recurrence fingerprint")
    hist_parser.add_argument("--limit", "-l", type=int, default=10, help="Max records to return")
    hist_parser.add_argument("--db-path", default=None, help="Custom SQLite ledger path")

    # Verb 4: audit-architecture
    audit_parser = subparsers.add_parser("audit-architecture", help="Audit infrastructure against the 7 Resonant Invariants of Distributed Resilience")
    audit_parser.add_argument(
        "--incident",
        "-i",
        required=True,
        help="Path to incident file or preset name",
    )

    args = parser.parse_args()

    if args.command == "synthesize":
        return handle_synthesize(args)
    elif args.command == "verify":
        return handle_verify(args)
    elif args.command == "history":
        return handle_history(args)
    elif args.command == "audit-architecture":
        return handle_audit_architecture(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
