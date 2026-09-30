from app.services.clinical_service import ClinicalService


class FakeMapping:
    def resolve(self, name):
        return {
            "input_name": name, "product_id": "P1", "product_name": name,
            "normalized_product_name": name.lower(), "generic_name": name,
            "product_match_method": "EXACT_NORMALIZED_PRODUCT_NAME",
            "mapping_status": "RESOLVED", "ingredients": []
        }


class FakeDDI:
    def check(self, medicines, use_gnn_fallback=True):
        return {
            "requested_medicines": medicines, "medicine_resolutions": [],
            "resolved_drug_count": 2, "pairs_checked": 1,
            "known_interaction_count": 1, "predicted_interaction_count": 0,
            "highest_severity": "Moderate", "has_major_interaction": False,
            "unresolved_medicines": [],
            "interactions": [{
                "medicine_a": medicines[0], "medicine_b": medicines[1],
                "status": "KNOWN_INTERACTION", "severity": "Moderate"
            }]
        }


class FakeDosage:
    def check(self, medicine_name, **kwargs):
        return {
            "medicine_resolution": FakeMapping().resolve(medicine_name),
            "canonical_drug_ids": [], "canonical_drug_names": [],
            "status": "DOSAGE_RULES_FOUND", "selection_strategy": "STANDARD",
            "matched_disease": kwargs.get("disease"), "matched_route": kwargs.get("route"),
            "standard_or_disease_rules": [{}], "renal_adjustments": [],
            "warnings": [], "disclaimer": "x"
        }


class FakePGx:
    def check(self, medicine_name, gene_symbol, variants):
        return {
            "medicine_resolution": FakeMapping().resolve(medicine_name),
            "canonical_drug_ids": [], "canonical_drug_names": [],
            "status": "NO_PGX_RULE_FOR_DRUG", "gene_symbol": gene_symbol,
            "implementation_scope": "TPMT_ONLY", "supplied_variants": variants,
            "matched_variants": [], "drug_rules": [], "pgx_relevant": False,
            "warnings": [], "disclaimer": "x"
        }


class FakeAlt:
    def recommend(self, medicine_name, other_medicines, max_alternatives, use_gnn_fallback):
        return {
            "source_medicine": FakeMapping().resolve(medicine_name),
            "source_product_id": "P1", "source_product_name": medicine_name,
            "other_medicines": other_medicines, "status": "ALTERNATIVES_FOUND",
            "candidates_found": 1, "candidates_returned": 1, "alternatives": [],
            "warnings": [], "disclaimer": "x"
        }


def build_service():
    service = object.__new__(ClinicalService)
    service.mapping_service = FakeMapping()
    service.ddi_service = FakeDDI()
    service.dosage_service = FakeDosage()
    service.pgx_service = FakePGx()
    service.alternative_service = FakeAlt()
    return service


def test_integrated_analysis_triggers_alternatives_for_moderate_ddi():
    result = build_service().analyze(
        ["Drug A", "Drug B"], age_years=30, weight_kg=70,
        disease="Test", route="IV", crcl_ml_min=80, include_alternatives=True
    )
    assert result["status"] == "CLINICAL_ANALYSIS_COMPLETED"
    assert result["summary"]["highest_ddi_severity"] == "Moderate"
    assert result["alternatives_status"] == "COMPLETED"
    assert result["summary"]["alternatives_evaluated_for"] == 2
    assert result["summary"]["attention_level"] == "REVIEW"


def test_single_medicine_skips_ddi_and_alternatives():
    result = build_service().analyze(["Drug A"], include_alternatives=True)
    assert result["ddi_status"] == "NOT_RUN_SINGLE_MEDICINE"
    assert result["alternatives_status"] == "NOT_TRIGGERED_NO_MODERATE_OR_MAJOR_DDI"
    assert result["ddi_analysis"] is None
