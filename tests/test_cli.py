import os
import subprocess
import pytest
from post_agi_runbook_synthesizer.cli import main
import sys


def test_cli_synthesize_preset(tmp_path, monkeypatch):
    out_dir = str(tmp_path / "cli_out")
    db_file = str(tmp_path / "cli_db.sqlite")

    test_args = [
        "runbook",
        "synthesize",
        "--incident",
        "proxy_buffer_bloat",
        "--output",
        out_dir,
        "--db-path",
        db_file,
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    ret = main()
    assert ret == 0

    assert os.path.exists(os.path.join(out_dir, "runbook.md"))
    assert os.path.exists(os.path.join(out_dir, "alerts.yaml"))
    assert os.path.exists(os.path.join(out_dir, "test_canary_probe.py"))

    # Test history retrieval CLI
    hist_args = ["runbook", "history", "--db-path", db_file]
    monkeypatch.setattr(sys, "argv", hist_args)
    ret_hist = main()
    assert ret_hist == 0

    # Test verify CLI
    ver_args = ["runbook", "verify", os.path.join(out_dir, "test_canary_probe.py")]
    monkeypatch.setattr(sys, "argv", ver_args)
    ret_ver = main()
    assert ret_ver == 0
