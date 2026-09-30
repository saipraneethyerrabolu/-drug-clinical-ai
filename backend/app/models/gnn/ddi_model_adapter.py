from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import DDI_MODEL_FILE


@dataclass
class DDIGNNModelAdapter:
    """Safe hook for the Weighted GNN used in a later integration step.

    Phase 2 intentionally does not fabricate predictions. If a compatible
    trained model artifact is not present and wired to its graph features, the
    adapter reports MODEL_NOT_CONFIGURED instead of guessing a severity.
    """

    model_path: Path = DDI_MODEL_FILE

    @property
    def available(self) -> bool:
        return self.model_path.exists()

    def predict(self, drug_a_canonical_id: str, drug_b_canonical_id: str) -> dict:
        if not self.available:
            return {
                "status": "MODEL_NOT_CONFIGURED",
                "severity": None,
                "confidence": None,
                "note": "No compatible Weighted GNN artifact is configured in this Phase 2 package.",
            }

        # A .pt file alone is not enough: prediction must use the exact graph,
        # node-index mapping, feature construction and class mapping used at
        # training time. Those artifacts are connected in the GNN integration
        # phase rather than silently assuming incompatible preprocessing here.
        return {
            "status": "MODEL_ARTIFACT_PRESENT_NOT_WIRED",
            "severity": None,
            "confidence": None,
            "note": "Model file exists, but graph/node mapping integration is required before inference.",
        }
