"""Base stage definitions and pipeline execution context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from post_agi_runbook_synthesizer.models import (
    AlertRule,
    CanaryProbeSpec,
    CircuitBreakerConfig,
    CustomerAdvisory,
    IngestedIncident,
    PostMortemRecord,
    RemediationAction,
    SLIBurn,
    TopologyModel,
)


class PipelineContext(BaseModel):
    """Execution context carrying state across all 8 pipeline stages."""

    incident: IngestedIncident
    sli_burns: List[SLIBurn] = Field(default_factory=list)
    topology: Optional[TopologyModel] = None
    circuit_breaker: Optional[CircuitBreakerConfig] = None
    remediation_actions: List[RemediationAction] = Field(default_factory=list)
    canary_spec: Optional[CanaryProbeSpec] = None
    customer_advisory: Optional[CustomerAdvisory] = None
    internal_advisory: Optional[str] = None
    ledger_record: Optional[PostMortemRecord] = None
    similar_past_incidents: List[Dict[str, str]] = Field(default_factory=list)
    alerts: List[AlertRule] = Field(default_factory=list)
    runbook_markdown: Optional[str] = None
    alerts_yaml_content: Optional[str] = None
    canary_probe_code: Optional[str] = None


class BaseStage(ABC):
    """Abstract base class for all SRE synthesizer stages."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the SRE stage."""
        pass

    @property
    @abstractmethod
    def s_domain(self) -> str:
        """Theoretical and SRE engineering domain."""
        pass

    @abstractmethod
    def execute(self, ctx: PipelineContext) -> PipelineContext:
        """Execute this stage's transformations on the pipeline context."""
        pass
