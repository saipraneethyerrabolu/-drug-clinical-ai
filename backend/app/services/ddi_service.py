from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math

from app.loaders.ddi_loader import load_interactions
from app.models.gnn.ddi_model_adapter import DDIGNNModelAdapter
from app.services.medicine_mapping_service import MedicineMappingService


def _clean(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text if text and text.lower() != "nan" else None


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


SEVERITY_RANK = {"Unknown": 0, "Minor": 1, "Moderate": 2, "Major": 3}


@dataclass
class DDIService:
    mapping_service: MedicineMappingService | None = None
    model_adapter: DDIGNNModelAdapter | None = None

    def __post_init__(self):
        self.mapping_service = self.mapping_service or MedicineMappingService()
        self.model_adapter = self.model_adapter or DDIGNNModelAdapter()
        self.interactions = load_interactions()

        self._by_canonical_pair: dict[tuple[str, str], dict] = {}
        self._by_ddinter_pair: dict[tuple[str, str], dict] = {}

        # itertuples is substantially faster than iterrows for the 160k-row DDI table.
        for row in self.interactions.itertuples(index=False):
            record = {
                "ddi_id": _clean(getattr(row, "ddi_id", None)),
                "ddinter_id_a": _clean(getattr(row, "ddinter_id_a", None)),
                "drug_a": _clean(getattr(row, "drug_a", None)),
                "ddinter_id_b": _clean(getattr(row, "ddinter_id_b", None)),
                "drug_b": _clean(getattr(row, "drug_b", None)),
                "severity": _clean(getattr(row, "severity", None)) or "Unknown",
                "drug_a_canonical_id": _clean(getattr(row, "drug_a_canonical_id", None)),
                "drug_b_canonical_id": _clean(getattr(row, "drug_b_canonical_id", None)),
                "canonical_mapping_status": _clean(getattr(row, "canonical_mapping_status", None)),
            }

            ca, cb = record["drug_a_canonical_id"], record["drug_b_canonical_id"]
            if ca and cb:
                self._by_canonical_pair[_pair_key(ca, cb)] = record

            da, db = record["ddinter_id_a"], record["ddinter_id_b"]
            if da and db:
                self._by_ddinter_pair[_pair_key(da, db)] = record

    def _flatten_resolved_drugs(self, medicine_names: list[str]) -> tuple[list[dict], list[dict]]:
        medicines: list[dict] = []
        drugs: list[dict] = []

        for index, medicine_name in enumerate(medicine_names):
            resolution = self.mapping_service.resolve(medicine_name)
            medicines.append(resolution)

            for ingredient in resolution.get("ingredients", []):
                if ingredient.get("mapping_status") != "RESOLVED":
                    continue
                canonical_id = ingredient.get("canonical_drug_id")
                if not canonical_id:
                    continue
                drugs.append(
                    {
                        "medicine_index": index,
                        "input_name": medicine_name,
                        "product_id": resolution.get("product_id"),
                        "product_name": resolution.get("product_name"),
                        "canonical_drug_id": canonical_id,
                        "canonical_name": ingredient.get("canonical_name"),
                        "ddinter_id": ingredient.get("ddinter_id"),
                        "drugbank_id": ingredient.get("drugbank_id"),
                    }
                )

        return medicines, drugs

    def _lookup_known(self, drug_a: dict, drug_b: dict) -> dict | None:
        ca, cb = drug_a.get("canonical_drug_id"), drug_b.get("canonical_drug_id")
        if ca and cb:
            hit = self._by_canonical_pair.get(_pair_key(ca, cb))
            if hit:
                return hit

        da, db = drug_a.get("ddinter_id"), drug_b.get("ddinter_id")
        if da and db:
            return self._by_ddinter_pair.get(_pair_key(da, db))
        return None

    def check(self, medicine_names: list[str], use_gnn_fallback: bool = True) -> dict:
        medicines, resolved_drugs = self._flatten_resolved_drugs(medicine_names)
        pair_results: list[dict] = []

        # Only compare ingredients coming from different medicine inputs. This
        # avoids reporting interactions between ingredients of the same combo product.
        for drug_a, drug_b in combinations(resolved_drugs, 2):
            if drug_a["medicine_index"] == drug_b["medicine_index"]:
                continue

            known = self._lookup_known(drug_a, drug_b)
            base = {
                "medicine_a": drug_a["input_name"],
                "medicine_b": drug_b["input_name"],
                "product_a": drug_a.get("product_name"),
                "product_b": drug_b.get("product_name"),
                "drug_a": drug_a.get("canonical_name"),
                "drug_b": drug_b.get("canonical_name"),
                "drug_a_canonical_id": drug_a.get("canonical_drug_id"),
                "drug_b_canonical_id": drug_b.get("canonical_drug_id"),
                "ddinter_id_a": drug_a.get("ddinter_id"),
                "ddinter_id_b": drug_b.get("ddinter_id"),
            }

            if known:
                pair_results.append(
                    {
                        **base,
                        "status": "KNOWN_INTERACTION",
                        "severity": known["severity"],
                        "source": "DDInter/unified dataset",
                        "ddi_id": known["ddi_id"],
                        "model_status": "NOT_USED_KNOWN_INTERACTION",
                        "model_confidence": None,
                    }
                )
                continue

            model_result = (
                self.model_adapter.predict(
                    drug_a["canonical_drug_id"], drug_b["canonical_drug_id"]
                )
                if use_gnn_fallback
                else {
                    "status": "MODEL_FALLBACK_DISABLED",
                    "severity": None,
                    "confidence": None,
                }
            )

            if model_result.get("severity"):
                pair_results.append(
                    {
                        **base,
                        "status": "MODEL_PREDICTED_INTERACTION",
                        "severity": model_result["severity"],
                        "source": "Weighted GNN",
                        "ddi_id": None,
                        "model_status": model_result.get("status"),
                        "model_confidence": model_result.get("confidence"),
                    }
                )
            else:
                pair_results.append(
                    {
                        **base,
                        "status": "NO_KNOWN_INTERACTION",
                        "severity": None,
                        "source": "DDInter/unified dataset",
                        "ddi_id": None,
                        "model_status": model_result.get("status"),
                        "model_confidence": model_result.get("confidence"),
                    }
                )

        unresolved = [
            {
                "input_name": item.get("input_name"),
                "mapping_status": item.get("mapping_status"),
                "product_name": item.get("product_name"),
            }
            for item in medicines
            if item.get("mapping_status") != "RESOLVED"
        ]

        severities = [r["severity"] for r in pair_results if r.get("severity")]
        highest_severity = (
            max(severities, key=lambda s: SEVERITY_RANK.get(s, -1)) if severities else None
        )
        known_count = sum(r["status"] == "KNOWN_INTERACTION" for r in pair_results)
        predicted_count = sum(r["status"] == "MODEL_PREDICTED_INTERACTION" for r in pair_results)

        return {
            "requested_medicines": medicine_names,
            "medicine_resolutions": medicines,
            "resolved_drug_count": len(resolved_drugs),
            "pairs_checked": len(pair_results),
            "known_interaction_count": known_count,
            "predicted_interaction_count": predicted_count,
            "highest_severity": highest_severity,
            "has_major_interaction": highest_severity == "Major",
            "unresolved_medicines": unresolved,
            "interactions": pair_results,
        }
