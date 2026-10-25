import os
import sys
import pytest
from post_agi_runbook_synthesizer.pipeline import SynthesizerPipeline
from post_agi_runbook_synthesizer.presets import get_proxy_buffer_bloat_incident


def test_synthesized_canary_probe_execution(tmp_path):
    """End-to-end test: synthesize artifacts and execute the generated canary probe."""
    output_dir = str(tmp_path / "canary_test_output")
    incident = get_proxy_buffer_bloat_incident()

    pipeline = SynthesizerPipeline(output_dir=output_dir, db_path=str(tmp_path / "ledger.db"))
    ctx = pipeline.run(incident)

    canary_script = os.path.join(output_dir, "test_canary_probe.py")
    assert os.path.exists(canary_script)

    sys.modules.pop("test_canary_probe", None)
    exit_code = pytest.main(["-v", "--import-mode=importlib", "-o", "asyncio_default_fixture_loop_scope=function", canary_script])
    assert exit_code == 0, "Synthesized canary probe failed to pass verification"
