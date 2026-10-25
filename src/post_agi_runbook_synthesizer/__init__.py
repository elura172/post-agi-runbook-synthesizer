"""Post-AGI Runbook Synthesizer.

Automated SRE incident-to-runbook compiler, synthetic canary generator,
and alerting synthesizer for distributed AI infrastructure.
"""

__version__ = "0.2.0"

from post_agi_runbook_synthesizer.models import (
    FailureDomain,
    IncidentBundle,
    IngestedIncident,
    Severity,
    TelemetryMetrics,
)
from post_agi_runbook_synthesizer.pipeline import SynthesizerPipeline

__all__ = [
    "__version__",
    "FailureDomain",
    "Severity",
    "TelemetryMetrics",
    "IngestedIncident",
    "IncidentBundle",
    "SynthesizerPipeline",
]
