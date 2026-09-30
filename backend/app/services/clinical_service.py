from __future__ import annotations

from dataclasses import dataclass

from app.services.alternative_service import AlternativeService
from app.services.ddi_service import DDIService
from app.services.dosage_service import DosageService
from app.services.medicine_mapping_service import MedicineMappingService
from app.services.pgx_service import PGxService


@dataclass
class ClinicalService:
    mapping_service: MedicineMappingService | None = None

    def __post_init__(self):
        # Share the expensive medicine mapping tables across all Phase 6 modules.
        self.mapping_service = self.mapping_service or MedicineMappingService()
        self.ddi_service = DDIService(mapping_service=self.mapping_service)
        self.dosage_service = DosageService(mapping_service=self.mapping_service)
        self.pgx_service = PGxService(mapping_service=self.mapping_service)
        self.alternative_service = AlternativeService(
            mapping_service=self.mapping_service,
            ddi_service=self.ddi_service,
        )

    @staticmethod
    def _problem_medicines(ddi: dict | None) -> list[str]:
        if not ddi:
            return []
        found: list[str] = []
        for item in ddi.get("interactions", []):
            if item.get("severity") not in {"Moderate", "Major"}:
                continue
            for key in ("medicine_a", "medicine_b"):
                name = item.get(key)
                if name and name not in found:
                    found.append(name)
        return found

    @staticmethod
    def _attention_level(ddi: dict | None, pgx_results: list[dict], dosage_results: list[dict]) -> str:
        if ddi and ddi.get("highest_severity") == "Major":
            return "HIGH"
        if ddi and ddi.get("highest_severity") == "Moderate":
            return "REVIEW"
        if any(x.get("status") == "PGX_RULE_AND_VARIANT_FOUND" for x in pgx_results):
            return "REVIEW"
        if any(x.get("renal_adjustments") for x in dosage_results):
            return "REVIEW"
        return "STANDARD_REVIEW"

    def analyze(
        self,
        medicines: list[str],
        age_years=None,
        weight_kg=None,
        disease=None,
        route=None,
        crcl_ml_min=None,
        gene_symbol: str = "TPMT",
        variants: list[str] | None = None,
        use_gnn_fallback: bool = True,
        include_alternatives: bool = True,
        max_alternative_sources: int = 2,
        max_alternatives_per_medicine: int = 3,
    ) -> dict:
        variants = variants or []
        warnings: list[str] = []

        # Resolve once for the top-level report. Individual services reuse the same
        # mapping service, so their internal lookups stay consistent.
        medicine_resolutions = [self.mapping_service.resolve(name) for name in medicines]

        ddi = None
        if len(medicines) >= 2:
            ddi = self.ddi_service.check(medicines, use_gnn_fallback=use_gnn_fallback)
            ddi_status = "COMPLETED"
        else:
            ddi_status = "NOT_RUN_SINGLE_MEDICINE"
            warnings.append("DDI analysis requires at least two medicines and was not run.")

        dosage_results = [
            self.dosage_service.check(
                medicine_name=name,
                age_years=age_years,
                weight_kg=weight_kg,
                disease=disease,
                route=route,
                crcl_ml_min=crcl_ml_min,
            )
            for name in medicines
        ]

        pgx_results = [
            self.pgx_service.check(name, gene_symbol or "TPMT", variants)
            for name in medicines
        ]

        alternative_results: list[dict] = []
        problem_medicines = self._problem_medicines(ddi)
        if not include_alternatives:
            alternatives_status = "DISABLED_BY_REQUEST"
        elif not problem_medicines:
            alternatives_status = "NOT_TRIGGERED_NO_MODERATE_OR_MAJOR_DDI"
        else:
            selected_sources = problem_medicines[:max_alternative_sources]
            for source_name in selected_sources:
                other_medicines = [m for m in medicines if m != source_name]
                alternative_results.append(
                    self.alternative_service.recommend(
                        medicine_name=source_name,
                        other_medicines=other_medicines,
                        max_alternatives=max_alternatives_per_medicine,
                        use_gnn_fallback=use_gnn_fallback,
                    )
                )
            alternatives_status = "COMPLETED" if alternative_results else "NO_RESULTS"
            if len(problem_medicines) > max_alternative_sources:
                warnings.append(
                    f"Alternative analysis was limited to the first {max_alternative_sources} medicines involved in Moderate/Major interactions."
                )

        resolved_count = sum(r.get("mapping_status") == "RESOLVED" for r in medicine_resolutions)
        dosage_found = sum(r.get("status") == "DOSAGE_RULES_FOUND" for r in dosage_results)
        renal_found = sum(bool(r.get("renal_adjustments")) for r in dosage_results)
        pgx_relevant = sum(bool(r.get("pgx_relevant")) for r in pgx_results)
        pgx_variant_matches = sum(r.get("status") == "PGX_RULE_AND_VARIANT_FOUND" for r in pgx_results)

        review_flags: list[str] = []
        if ddi:
            severity = ddi.get("highest_severity")
            if severity:
                review_flags.append(f"DDI_{severity.upper()}")
        if pgx_variant_matches:
            review_flags.append("PGX_MATCHED_VARIANT")
        elif any(r.get("pgx_relevant") for r in pgx_results):
            review_flags.append("PGX_RULE_PRESENT")
        if renal_found:
            review_flags.append("RENAL_ADJUSTMENT_AVAILABLE")
        if dosage_found < len(medicines):
            review_flags.append("DOSAGE_INFORMATION_REQUIRES_CLINICIAN_REVIEW")
        if resolved_count < len(medicines):
            review_flags.append("UNRESOLVED_MEDICINE")

        narrative = [
            f"Resolved {resolved_count} of {len(medicines)} requested medicine products.",
        ]
        if ddi:
            if ddi.get("highest_severity"):
                narrative.append(
                    f"DDI analysis checked {ddi.get('pairs_checked', 0)} ingredient pairs; highest dataset/model severity was {ddi.get('highest_severity')}."
                )
            else:
                narrative.append(
                    f"DDI Assessment: No Known Interaction Detected. Checked {ddi.get('pairs_checked', 0)} ingredient pairs; no known interaction was identified in the configured interaction data."
                )
        else:
            narrative.append("DDI analysis was not applicable because only one medicine was supplied.")
        narrative.append(
            f"Dosage information was available for {dosage_found} of {len(medicines)} medicines; renal adjustment information matched for {renal_found}. Medicines without matching local dosage information can be checked against the official FDA label reference in the dosage view."
        )
        narrative.append(
            f"TPMT PGx rules were relevant for {pgx_relevant} medicines; supplied variants matched implemented PGx evidence for {pgx_variant_matches}."
        )
        if alternative_results:
            narrative.append(
                f"Alternative products were evaluated for {len(alternative_results)} medicines involved in Moderate/Major DDI findings, with automatic DDI re-check."
            )
        elif alternatives_status == "NOT_TRIGGERED_NO_MODERATE_OR_MAJOR_DDI":
            narrative.append("Alternative analysis was not triggered because no Moderate/Major DDI was found.")

        # De-duplicate module warnings while preserving order.
        for result in dosage_results + pgx_results + alternative_results:
            for warning in result.get("warnings", []):
                if warning not in warnings:
                    warnings.append(warning)
        if ddi:
            for unresolved in ddi.get("unresolved_medicines", []):
                msg = f"Medicine mapping incomplete for: {unresolved.get('input_name')}."
                if msg not in warnings:
                    warnings.append(msg)

        summary = {
            "medicines_requested": len(medicines),
            "medicines_resolved": resolved_count,
            "ddi_status": ddi_status,
            "highest_ddi_severity": ddi.get("highest_severity") if ddi else None,
            "known_interactions": ddi.get("known_interaction_count", 0) if ddi else 0,
            "predicted_interactions": ddi.get("predicted_interaction_count", 0) if ddi else 0,
            "dosage_rules_found_for": dosage_found,
            "renal_adjustments_found_for": renal_found,
            "pgx_relevant_for": pgx_relevant,
            "pgx_variant_matches_for": pgx_variant_matches,
            "alternatives_evaluated_for": len(alternative_results),
            "attention_level": self._attention_level(ddi, pgx_results, dosage_results),
            "review_flags": review_flags,
            "narrative": narrative,
        }

        return {
            "status": "CLINICAL_ANALYSIS_COMPLETED",
            "patient_context": {
                "age_years": age_years,
                "weight_kg": weight_kg,
                "disease": disease,
                "route": route,
                "crcl_ml_min": crcl_ml_min,
                "gene_symbol": (gene_symbol or "TPMT").upper(),
                "variants": variants,
            },
            "medicine_resolutions": medicine_resolutions,
            "ddi_status": ddi_status,
            "ddi_analysis": ddi,
            "dosage_analyses": dosage_results,
            "pgx_analyses": pgx_results,
            "alternatives_status": alternatives_status,
            "alternative_analyses": alternative_results,
            "summary": summary,
            "warnings": warnings,
            "disclaimer": (
                "Dataset-backed educational clinical decision-support output only. It is not a diagnosis, prescription, "
                "or substitute for clinician/pharmacist/genetics review. Known dataset interactions are preferred over "
                "model predictions, and PGx support is limited to TPMT in the supplied files."
            ),
        }
