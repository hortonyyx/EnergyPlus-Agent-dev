"""Staged phase-2 correction layer.

phase2a (LLM correction) -> CorrectedGeometry  (materialized intermediate)
   -> deterministic core (code: canonical axis snap + sliver guard)
   -> phase2b (LLM modeling) -> IntakeOutput

Decoupling the stages makes each model swappable and the correction checkpoint
verifiable / diffable for evaluation. Spec: skills/intake_pipeline/ (1_correction + 4_mep)
PartA-correction/.
"""

from src.agent.correction.deterministic import apply_deterministic_core
from src.agent.correction.schema import CorrectedGeometry

__all__ = ["CorrectedGeometry", "apply_deterministic_core"]
