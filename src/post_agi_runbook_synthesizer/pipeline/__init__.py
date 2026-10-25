"""The 8-Stage Cognitive SRE Pipeline for Post-AGI Runbook Synthesizer."""

from __future__ import annotations

from typing import List, Optional
from post_agi_runbook_synthesizer.models import IncidentBundle, IngestedIncident
from post_agi_runbook_synthesizer.pipeline.base import BaseStage, PipelineContext
from post_agi_runbook_synthesizer.pipeline.circuit_breaker import CircuitBreakerStage
from post_agi_runbook_synthesizer.pipeline.comms import CommsStage
from post_agi_runbook_synthesizer.pipeline.falsifier import FalsifierStage
from post_agi_runbook_synthesizer.pipeline.orchestrator import OrchestratorStage
from post_agi_runbook_synthesizer.pipeline.postmortem_ledger import (
    DEFAULT_LEDGER_PATH,
    PostmortemLedgerStage,
)
from post_agi_runbook_synthesizer.pipeline.remediation import RemediationStage
from post_agi_runbook_synthesizer.pipeline.telemetry import TelemetryStage
from post_agi_runbook_synthesizer.pipeline.topology import TopologyStage


class SynthesizerPipeline:
    """End-to-End Orchestrator running all 8 cognitive SRE stages in sequence."""

    def __init__(
        self,
        output_dir: str = "./artifacts",
        db_path: str = DEFAULT_LEDGER_PATH,
    ):
        self.output_dir = output_dir
        self.db_path = db_path
        self.stages: List[BaseStage] = [
            TelemetryStage(),
            TopologyStage(),
            CircuitBreakerStage(),
            RemediationStage(),
            FalsifierStage(),
            CommsStage(),
            PostmortemLedgerStage(db_path=self.db_path),
            OrchestratorStage(output_dir=self.output_dir),
        ]

    def run(self, incident: IngestedIncident) -> PipelineContext:
        ctx = PipelineContext(incident=incident)
        for stage in self.stages:
            ctx = stage.execute(ctx)
        return ctx


__all__ = [
    "BaseStage",
    "PipelineContext",
    "TelemetryStage",
    "TopologyStage",
    "CircuitBreakerStage",
    "RemediationStage",
    "FalsifierStage",
    "CommsStage",
    "PostmortemLedgerStage",
    "OrchestratorStage",
    "SynthesizerPipeline",
]
