import os
import pytest
from post_agi_runbook_synthesizer.models import FailureDomain, Severity
from post_agi_runbook_synthesizer.parsers.generic_parser import load_incident_from_file
from post_agi_runbook_synthesizer.parsers.sentinel_parser import parse_sentinel_markdown


FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "../fixtures/sample-sentinel-incident.md")


def test_parse_sentinel_markdown():
    incident = load_incident_from_file(FIXTURE_PATH)

    assert incident.incident_id == "INC-4FB1577E"
    assert incident.target_model == "gpt-4o"
    assert incident.domain == FailureDomain.PROXY_BUFFER_BLOAT
    assert incident.severity == Severity.SEV_3
    assert "MIT 6.033" in incident.theoretical_grounding
    assert incident.telemetry.ttft_ms == 262.10
    assert incident.telemetry.token_cadence_tps == 16.96
    assert incident.telemetry.p95_jitter_ms == 1.21
    assert incident.telemetry.chunks_observed == 32
    assert incident.telemetry.prompt_cache_hit is False
    assert len(incident.remediation_notes) > 0


def test_load_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        load_incident_from_file("/tmp/nonexistent-incident.md")
