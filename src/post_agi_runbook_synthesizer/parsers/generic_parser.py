"""Generic incident file loader for markdown, json, or yaml sources."""

from __future__ import annotations

import json
import os
import yaml
from post_agi_runbook_synthesizer.models import IngestedIncident
from post_agi_runbook_synthesizer.parsers.sentinel_parser import (
    parse_sentinel_json,
    parse_sentinel_markdown,
)


def load_incident_from_file(file_path: str) -> IngestedIncident:
    """Load an incident from a file path (.md, .json, .yaml)."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Incident file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".json":
        try:
            return parse_sentinel_json(content)
        except Exception:
            data = json.loads(content)
            return IngestedIncident(**data)
    elif ext in [".yaml", ".yml"]:
        data = yaml.safe_load(content)
        return IngestedIncident(**data)
    else:
        # Default to markdown parser
        return parse_sentinel_markdown(content)
