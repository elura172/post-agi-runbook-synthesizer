"""Stage 7: Historical Post-Mortem Ledger & Recurrence Fingerprinting.

Grounding: SRE Incident Management & Post-Mortem Compendium, Distributed Systems Memory Continuity.
Stores structured post-mortems in an SQLite ledger, computes recurrence fingerprints,
and queries historical outages to prevent recurring architectural toil.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional
from post_agi_runbook_synthesizer.models import PostMortemRecord
from post_agi_runbook_synthesizer.pipeline.base import BaseStage, PipelineContext


DEFAULT_LEDGER_PATH = os.path.expanduser("~/.runbooks/incident_ledger.db")


def init_db(db_path: str = DEFAULT_LEDGER_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS postmortems (
                incident_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                domain TEXT NOT NULL,
                severity TEXT NOT NULL,
                theoretical_grounding TEXT NOT NULL,
                root_cause_summary TEXT NOT NULL,
                blast_radius_summary TEXT NOT NULL,
                remediation_summary TEXT NOT NULL,
                recurrence_fingerprint TEXT NOT NULL,
                mttr_seconds INTEGER DEFAULT 0,
                raw_data TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_domain ON postmortems (domain)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fingerprint ON postmortems (recurrence_fingerprint)")


def store_postmortem(record: PostMortemRecord, raw_data: Dict[str, Any], db_path: str = DEFAULT_LEDGER_PATH) -> None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO postmortems (
                incident_id, timestamp, domain, severity, theoretical_grounding,
                root_cause_summary, blast_radius_summary, remediation_summary,
                recurrence_fingerprint, mttr_seconds, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.incident_id,
                record.timestamp,
                record.domain.value,
                record.severity.value,
                record.theoretical_grounding,
                record.root_cause_summary,
                record.blast_radius_summary,
                record.remediation_summary,
                record.recurrence_fingerprint,
                record.mttr_seconds,
                json.dumps(raw_data),
            ),
        )


def query_historical_incidents(
    domain: Optional[str] = None,
    fingerprint: Optional[str] = None,
    limit: int = 5,
    db_path: str = DEFAULT_LEDGER_PATH,
) -> List[Dict[str, Any]]:
    if not os.path.exists(db_path):
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if fingerprint:
            cursor.execute(
                "SELECT incident_id, timestamp, domain, severity, root_cause_summary, mttr_seconds "
                "FROM postmortems WHERE recurrence_fingerprint = ? ORDER BY timestamp DESC LIMIT ?",
                (fingerprint, limit),
            )
        elif domain:
            cursor.execute(
                "SELECT incident_id, timestamp, domain, severity, root_cause_summary, mttr_seconds "
                "FROM postmortems WHERE domain = ? ORDER BY timestamp DESC LIMIT ?",
                (domain, limit),
            )
        else:
            cursor.execute(
                "SELECT incident_id, timestamp, domain, severity, root_cause_summary, mttr_seconds "
                "FROM postmortems ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]


class PostmortemLedgerStage(BaseStage):
    """Stage 7: Historical ledger indexing and recurrence discovery."""

    def __init__(self, db_path: str = DEFAULT_LEDGER_PATH):
        self.db_path = db_path

    @property
    def name(self) -> str:
        return "postmortem_ledger_indexer"

    @property
    def s_domain(self) -> str:
        return "Historical Incident Continuity, Anti-Recurrence Fingerprinting & Knowledge Retrieval"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        incident = ctx.incident
        fault_node = ctx.topology.primary_fault_node if ctx.topology else "unknown"

        # Compute deterministic fingerprint based on structural failure pattern
        fingerprint_raw = f"{incident.domain.value}:{fault_node}:{incident.target_model}"
        fingerprint = hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()[:16]

        record = PostMortemRecord(
            incident_id=incident.incident_id,
            timestamp=incident.incident_id.split("-")[1] if "-" in incident.incident_id else "2026-10-24",
            domain=incident.domain,
            severity=incident.severity,
            theoretical_grounding=incident.theoretical_grounding,
            root_cause_summary=incident.executive_summary,
            blast_radius_summary=", ".join(ctx.topology.blast_radius_nodes) if ctx.topology else "system",
            remediation_summary="; ".join(a.title for a in ctx.remediation_actions),
            recurrence_fingerprint=fingerprint,
            mttr_seconds=1800,  # Estimated baseline MTTR: 30 minutes
        )

        # Store in SQLite ledger
        try:
            store_postmortem(record, incident.model_dump(), db_path=self.db_path)
            # Find past similar incidents
            past = query_historical_incidents(
                fingerprint=fingerprint, limit=5, db_path=self.db_path
            )
            # Filter out self
            ctx.similar_past_incidents = [p for p in past if p["incident_id"] != incident.incident_id]
        except Exception:
            # Fallback gracefully if filesystem permissions or sandbox limits apply
            ctx.similar_past_incidents = []

        ctx.ledger_record = record
        return ctx
