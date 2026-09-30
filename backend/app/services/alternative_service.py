from __future__ import annotations

from dataclasses import dataclass
import math

from app.loaders.alternative_loader import find_alternatives
from app.services.ddi_service import DDIService, SEVERITY_RANK
from app.services.medicine_mapping_service import MedicineMappingService


def _clean(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text if text and text.lower() != "nan" else None


def _split_ids(value) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    return [x.strip() for x in text.split("|") if x.strip()]


@dataclass
class AlternativeService:
    mapping_service: MedicineMappingService | None = None
    ddi_service: DDIService | None = None

    def __post_init__(self):
        self.mapping_service = self.mapping_service or MedicineMappingService()
        # DDI service is initialized lazily only when a re-check is requested.
        # This prevents duplicating the large DDI indexes during API startup.
        # The alternatives CSV is intentionally streamed per lookup to avoid
        # holding ~1.15M rows in memory during API startup.

    @staticmethod
    def _recommendation_class(ddi_result: dict) -> str:
        if ddi_result.get("has_major_interaction"):
            return "AVOID_MAJOR_DDI"
        severity = ddi_result.get("highest_severity")
        if severity == "Moderate":
            return "CAUTION_MODERATE_DDI"
        if severity == "Minor":
            return "LOWER_RISK_MINOR_DDI"
        if ddi_result.get("pairs_checked", 0) == 0:
            return "NOT_ASSESSABLE_NO_COMPARISON_MEDICINES"
        return "NO_KNOWN_DDI_FOUND"

    def recommend(
        self,
        medicine_name: str,
        other_medicines: list[str] | None = None,
        max_alternatives: int = 5,
        use_gnn_fallback: bool = True,
    ) -> dict:
        other_medicines = other_medicines or []
        source = self.mapping_service.resolve(medicine_name)
        warnings: list[str] = []

        product_id = source.get("product_id")
        if source.get("mapping_status") != "RESOLVED" or not product_id:
            return {
                "source_medicine": source,
                "source_product_id": product_id,
                "source_product_name": source.get("product_name"),
                "other_medicines": other_medicines,
                "status": "SOURCE_MEDICINE_NOT_RESOLVED",
                "candidates_found": 0,
                "candidates_returned": 0,
                "alternatives": [],
                "warnings": ["The source medicine must resolve to a product before alternatives can be looked up."],
                "disclaimer": "Dataset-backed educational alternatives only; substitutions require clinician/pharmacist review.",
            }

        rows = find_alternatives(product_id)
        if not rows:
            return {
                "source_medicine": source,
                "source_product_id": product_id,
                "source_product_name": source.get("product_name"),
                "other_medicines": other_medicines,
                "status": "NO_ALTERNATIVES_FOUND",
                "candidates_found": 0,
                "candidates_returned": 0,
                "alternatives": [],
                "warnings": ["No substitute rows were found for this exact source product in 08_alternatives.csv."],
                "disclaimer": "Dataset-backed educational alternatives only; substitutions require clinician/pharmacist review.",
            }

        evaluated = []
        for raw in rows[:max_alternatives]:
            row = {
                "alternative_id": _clean(raw.get("alternative_id")),
                "source_product_id": _clean(raw.get("source_product_id")),
                "source_product_name": _clean(raw.get("source_product_name")),
                "substitute_rank": int(raw.get("substitute_rank")) if _clean(raw.get("substitute_rank")) else None,
                "alternative_product_name": _clean(raw.get("alternative_product_name")) or "",
                "alternative_product_id": _clean(raw.get("alternative_product_id")),
                "source_canonical_drug_ids": _split_ids(raw.get("source_canonical_drug_ids")),
                "alternative_canonical_drug_ids": _split_ids(raw.get("alternative_canonical_drug_ids")),
                "canonical_mapping_status": _clean(raw.get("canonical_mapping_status")),
            }
            alt_name = row["alternative_product_name"]
            if other_medicines:
                if self.ddi_service is None:
                    self.ddi_service = DDIService(mapping_service=self.mapping_service)
                ddi = self.ddi_service.check([alt_name, *other_medicines], use_gnn_fallback=use_gnn_fallback)
                ddi_status = "RECHECK_COMPLETED"
            else:
                ddi = {
                    "highest_severity": None,
                    "has_major_interaction": False,
                    "known_interaction_count": 0,
                    "predicted_interaction_count": 0,
                    "pairs_checked": 0,
                    "interactions": [],
                }
                ddi_status = "NOT_RUN_NO_OTHER_MEDICINES"

            evaluated.append({
                **row,
                "ddi_recheck_status": ddi_status,
                "highest_severity": ddi.get("highest_severity"),
                "has_major_interaction": bool(ddi.get("has_major_interaction")),
                "known_interaction_count": int(ddi.get("known_interaction_count", 0)),
                "predicted_interaction_count": int(ddi.get("predicted_interaction_count", 0)),
                "interactions": ddi.get("interactions", []),
                "recommendation_class": self._recommendation_class(ddi),
            })

        # Rank safety first, then preserve dataset substitute order.
        evaluated.sort(
            key=lambda x: (
                SEVERITY_RANK.get(x.get("highest_severity") or "Unknown", 0),
                x.get("substitute_rank") or 999999,
            )
        )

        if not other_medicines:
            warnings.append("DDI re-check was not run because no other medicines were supplied.")

        return {
            "source_medicine": source,
            "source_product_id": product_id,
            "source_product_name": source.get("product_name"),
            "other_medicines": other_medicines,
            "status": "ALTERNATIVES_FOUND",
            "candidates_found": len(rows),
            "candidates_returned": len(evaluated),
            "alternatives": evaluated,
            "warnings": warnings,
            "disclaimer": "Dataset-backed educational alternatives and DDI re-check only; substitutions require clinician/pharmacist review.",
        }
