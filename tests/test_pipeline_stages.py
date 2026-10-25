import os
import tempfile
import pytest
from post_agi_runbook_synthesizer.models import FailureDomain, Severity, TelemetryMetrics, IngestedIncident
from post_agi_runbook_synthesizer.pipeline.base import PipelineContext
from post_agi_runbook_synthesizer.pipeline.circuit_breaker import CircuitBreakerStage
from post_agi_runbook_synthesizer.pipeline.comms import CommsStage
from post_agi_runbook_synthesizer.pipeline.falsifier import FalsifierStage
from post_agi_runbook_synthesizer.pipeline.orchestrator import OrchestratorStage
from post_agi_runbook_synthesizer.pipeline.postmortem_ledger import PostmortemLedgerStage, query_historical_incidents
from post_agi_runbook_synthesizer.pipeline.remediation import RemediationStage
from post_agi_runbook_synthesizer.pipeline.telemetry import TelemetryStage
from post_agi_runbook_synthesizer.pipeline.topology import TopologyStage
from post_agi_runbook_synthesizer.presets import get_proxy_buffer_bloat_incident, get_inference_shard_stall_incident, get_rate_limit_stampede_incident


@pytest.fixture
def base_context():
    incident = get_proxy_buffer_bloat_incident()
    return PipelineContext(incident=incident)


def test_telemetry_stage(base_context):
    stage = TelemetryStage()
    ctx = stage.execute(base_context)

    assert len(ctx.sli_burns) == 3
    # Check jitter SLI breached (125.4ms vs 30ms target)
    jitter_sli = next(s for s in ctx.sli_burns if s.sli_name == "streaming_chunk_jitter_p95_ms")
    assert jitter_sli.violates_slo is True
    assert jitter_sli.burn_rate_1h > 1.0
    assert len(ctx.alerts) >= 1
    assert any("OpenAIStreamChunkJitterAnomaly" in a.alert_name for a in ctx.alerts)


def test_topology_stage_proxy_bloat(base_context):
    stage = TopologyStage()
    ctx = stage.execute(base_context)

    assert ctx.topology is not None
    assert ctx.topology.primary_fault_node == "edge_proxy"
    assert "client_app" in ctx.topology.blast_radius_nodes
    assert "X-Accel-Buffering" in ctx.topology.invariant_violation


def test_topology_stage_inference_shard():
    ctx = PipelineContext(incident=get_inference_shard_stall_incident())
    stage = TopologyStage()
    ctx = stage.execute(ctx)

    assert ctx.topology.primary_fault_node == "inference_worker"
    assert "routing_mesh" in ctx.topology.blast_radius_nodes


def test_circuit_breaker_stage(base_context):
    stage = CircuitBreakerStage()
    ctx = stage.execute(base_context)

    assert ctx.circuit_breaker is not None
    assert ctx.circuit_breaker.failure_threshold == 5
    assert len(ctx.circuit_breaker.calculated_delays) == 5
    # Verify delays strictly respect max ceiling
    assert all(d <= ctx.circuit_breaker.backoff_max_ms for d in ctx.circuit_breaker.calculated_delays)


def test_remediation_stage(base_context):
    # Run topology first
    TopologyStage().execute(base_context)
    stage = RemediationStage()
    ctx = stage.execute(base_context)

    assert len(ctx.remediation_actions) >= 4
    # Check that rollback command exists for config patch
    patch_step = next(s for s in ctx.remediation_actions if "Patch" in s.title)
    assert patch_step.rollback_command is not None
    assert "nginx -s reload" in patch_step.rollback_command


def test_falsifier_stage(base_context):
    stage = FalsifierStage()
    ctx = stage.execute(base_context)

    assert ctx.canary_spec is not None
    assert ctx.canary_probe_code is not None
    assert "test_canary_streaming_invariants" in ctx.canary_probe_code
    assert "test_chaos_falsification_guard" in ctx.canary_probe_code


def test_comms_stage(base_context):
    TopologyStage().execute(base_context)
    stage = CommsStage()
    ctx = stage.execute(base_context)

    assert ctx.customer_advisory is not None
    assert ctx.customer_advisory.incident_id == "INC-4FB1577E"
    assert len(ctx.customer_advisory.mitigation_workaround) > 0
    assert "X-Accel-Buffering: no" in ctx.customer_advisory.mitigation_workaround[1]


def test_postmortem_ledger_stage(base_context, tmp_path):
    db_file = str(tmp_path / "test_ledger.db")
    TopologyStage().execute(base_context)
    RemediationStage().execute(base_context)
    stage = PostmortemLedgerStage(db_path=db_file)
    ctx = stage.execute(base_context)

    assert ctx.ledger_record is not None
    assert len(ctx.ledger_record.recurrence_fingerprint) == 16

    # Verify query
    results = query_historical_incidents(domain=FailureDomain.PROXY_BUFFER_BLOAT.value, db_path=db_file)
    assert len(results) == 1
    assert results[0]["incident_id"] == "INC-4FB1577E"


def test_orchestrator_stage(base_context, tmp_path):
    output_dir = str(tmp_path / "artifacts")
    # Run full prerequisites
    TelemetryStage().execute(base_context)
    TopologyStage().execute(base_context)
    CircuitBreakerStage().execute(base_context)
    RemediationStage().execute(base_context)
    FalsifierStage().execute(base_context)
    CommsStage().execute(base_context)
    PostmortemLedgerStage(db_path=str(tmp_path / "test.db")).execute(base_context)

    stage = OrchestratorStage(output_dir=output_dir)
    ctx = stage.execute(base_context)

    assert os.path.exists(os.path.join(output_dir, "runbook.md"))
    assert os.path.exists(os.path.join(output_dir, "alerts.yaml"))
    assert os.path.exists(os.path.join(output_dir, "test_canary_probe.py"))
    assert os.path.exists(os.path.join(output_dir, "customer_advisory.md"))
    assert os.path.exists(os.path.join(output_dir, "incident_ledger.json"))

    # Verify content in runbook.md
    with open(os.path.join(output_dir, "runbook.md"), "r") as f:
        runbook_text = f.read()
    assert "Operational SRE Runbook: INC-4FB1577E" in runbook_text
    assert "Circuit Breaker & Adaptive Damping Policy" in runbook_text
    assert "Executable Remediation Procedures" in runbook_text
