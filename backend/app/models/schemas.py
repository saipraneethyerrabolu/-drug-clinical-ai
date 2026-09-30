from pydantic import BaseModel, Field, field_validator


class MedicineSearchItem(BaseModel):
    product_id: str
    product_name: str
    generic_name: str | None = None
    manufacturer: str | None = None
    prescription_required: str | None = None


class ResolveMedicineRequest(BaseModel):
    medicine_name: str = Field(min_length=1)


class IngredientResolution(BaseModel):
    ingredient_raw: str | None = None
    ingredient_normalized: str | None = None
    canonical_drug_id: str | None = None
    canonical_name: str | None = None
    drugbank_id: str | None = None
    ddinter_id: str | None = None
    mapping_method: str
    mapping_status: str


class MedicineResolutionResponse(BaseModel):
    input_name: str
    product_id: str | None = None
    product_name: str | None = None
    normalized_product_name: str | None = None
    generic_name: str | None = None
    product_match_method: str
    mapping_status: str
    ingredients: list[IngredientResolution]


class DDICheckRequest(BaseModel):
    medicines: list[str] = Field(min_length=2, max_length=20)
    use_gnn_fallback: bool = True

    @field_validator("medicines")
    @classmethod
    def validate_medicine_names(cls, value: list[str]) -> list[str]:
        cleaned = [str(name).strip() for name in value if str(name).strip()]
        if len(cleaned) < 2:
            raise ValueError("At least two non-empty medicine names are required.")
        if len(cleaned) != len(value):
            raise ValueError("Medicine names cannot be empty.")
        return cleaned


class DDIPairResult(BaseModel):
    medicine_a: str
    medicine_b: str
    product_a: str | None = None
    product_b: str | None = None
    drug_a: str | None = None
    drug_b: str | None = None
    drug_a_canonical_id: str | None = None
    drug_b_canonical_id: str | None = None
    ddinter_id_a: str | None = None
    ddinter_id_b: str | None = None
    status: str
    severity: str | None = None
    source: str
    ddi_id: str | None = None
    model_status: str
    model_confidence: float | None = None


class DDIUnresolvedMedicine(BaseModel):
    input_name: str | None = None
    mapping_status: str | None = None
    product_name: str | None = None


class DDICheckResponse(BaseModel):
    requested_medicines: list[str]
    medicine_resolutions: list[MedicineResolutionResponse]
    resolved_drug_count: int
    pairs_checked: int
    known_interaction_count: int
    predicted_interaction_count: int
    highest_severity: str | None = None
    has_major_interaction: bool
    unresolved_medicines: list[DDIUnresolvedMedicine]
    interactions: list[DDIPairResult]


class DosageCheckRequest(BaseModel):
    medicine_name: str = Field(min_length=1)
    age_years: float | None = Field(default=None, ge=0, le=130)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    disease: str | None = None
    route: str | None = None
    crcl_ml_min: float | None = Field(default=None, ge=0, le=300)

    @field_validator("medicine_name", "disease", "route", mode="before")
    @classmethod
    def strip_optional_text(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class DosageRule(BaseModel):
    record_id: str
    rule_type: str
    generic: str | None = None
    disease: str | None = None
    route: str | None = None
    age_range: dict
    weight_range_kg: dict
    dose_fields: dict
    mapping_status: str | None = None


class RenalDosageRule(BaseModel):
    record_id: str
    generic: str | None = None
    disease: str | None = None
    route: str | None = None
    crcl_range_ml_min: dict
    weight_range_kg: dict
    dose_fields: dict
    flag: str | None = None
    mapping_status: str | None = None


class DosageCheckResponse(BaseModel):
    medicine_resolution: MedicineResolutionResponse
    canonical_drug_ids: list[str]
    canonical_drug_names: list[str]
    status: str
    selection_strategy: str
    matched_disease: str | None = None
    matched_route: str | None = None
    standard_or_disease_rules: list[DosageRule]
    renal_adjustments: list[RenalDosageRule]
    warnings: list[str]
    disclaimer: str


class OfficialLabelReferenceResponse(BaseModel):
    medicine_name: str
    status: str
    source: str
    indication: str | None = None
    route: str | None = None
    dosage_form_strength: str | None = None
    dosage_and_administration_available: bool = False
    dosage_and_administration_text: str | None = None
    matched_search_field: str | None = None
    source_url: str | None = None
    warnings: list[str] = []


class PGxCheckRequest(BaseModel):
    medicine_name: str = Field(min_length=1)
    gene_symbol: str = "TPMT"
    variants: list[str] = []

    @field_validator("medicine_name", "gene_symbol", mode="before")
    @classmethod
    def strip_pgx_text(cls, value):
        text = str(value).strip() if value is not None else ""
        return text

    @field_validator("variants")
    @classmethod
    def clean_variants(cls, value: list[str]) -> list[str]:
        return [str(v).strip() for v in value if str(v).strip()]


class PGxMatchedVariant(BaseModel):
    pgx_variant_id: str
    rsid: str
    variant_type: str | None = None
    clinical_significance: str | None = None
    defining_allele_relationship: str | None = None
    source: str | None = None


class PGxDrugRule(BaseModel):
    pgx_rule_id: str
    canonical_drug_id: str
    drug_name: str
    gene_symbol: str
    guideline_name: str | None = None
    source: str | None = None
    dosing_information: bool | None = None
    recommendation_available: bool | None = None
    alternate_drug_available: bool | None = None
    pediatric_applicable: bool | None = None
    recommendation_summary: str | None = None
    implementation_scope: str | None = None
    validation_status: str | None = None


class PGxCheckResponse(BaseModel):
    medicine_resolution: MedicineResolutionResponse
    canonical_drug_ids: list[str]
    canonical_drug_names: list[str]
    status: str
    gene_symbol: str
    implementation_scope: str
    supplied_variants: list[str]
    matched_variants: list[PGxMatchedVariant]
    drug_rules: list[PGxDrugRule]
    pgx_relevant: bool
    warnings: list[str]
    disclaimer: str


class AlternativeRecommendRequest(BaseModel):
    medicine_name: str = Field(min_length=1)
    other_medicines: list[str] = []
    max_alternatives: int = Field(default=5, ge=1, le=20)
    use_gnn_fallback: bool = True

    @field_validator("medicine_name", mode="before")
    @classmethod
    def strip_alt_medicine(cls, value):
        return str(value).strip() if value is not None else ""

    @field_validator("other_medicines")
    @classmethod
    def clean_other_medicines(cls, value: list[str]) -> list[str]:
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        if len(cleaned) != len(value):
            raise ValueError("Other medicine names cannot be empty.")
        return cleaned


class AlternativeCandidate(BaseModel):
    alternative_id: str | None = None
    substitute_rank: int | None = None
    alternative_product_id: str | None = None
    alternative_product_name: str
    source_canonical_drug_ids: list[str]
    alternative_canonical_drug_ids: list[str]
    canonical_mapping_status: str | None = None
    ddi_recheck_status: str
    highest_severity: str | None = None
    has_major_interaction: bool
    known_interaction_count: int
    predicted_interaction_count: int
    interactions: list[DDIPairResult]
    recommendation_class: str


class AlternativeRecommendResponse(BaseModel):
    source_medicine: MedicineResolutionResponse
    source_product_id: str | None = None
    source_product_name: str | None = None
    other_medicines: list[str]
    status: str
    candidates_found: int
    candidates_returned: int
    alternatives: list[AlternativeCandidate]
    warnings: list[str]
    disclaimer: str


class ClinicalAnalyzeRequest(BaseModel):
    medicines: list[str] = Field(min_length=1, max_length=20)
    age_years: float | None = Field(default=None, ge=0, le=130)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    disease: str | None = None
    route: str | None = None
    crcl_ml_min: float | None = Field(default=None, ge=0, le=300)
    gene_symbol: str = "TPMT"
    variants: list[str] = []
    use_gnn_fallback: bool = True
    include_alternatives: bool = True
    max_alternative_sources: int = Field(default=2, ge=1, le=5)
    max_alternatives_per_medicine: int = Field(default=3, ge=1, le=10)

    @field_validator("medicines")
    @classmethod
    def clean_clinical_medicines(cls, value: list[str]) -> list[str]:
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        if len(cleaned) != len(value):
            raise ValueError("Medicine names cannot be empty.")
        return cleaned

    @field_validator("disease", "route", "gene_symbol", mode="before")
    @classmethod
    def clean_clinical_text(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("variants")
    @classmethod
    def clean_clinical_variants(cls, value: list[str]) -> list[str]:
        return [str(v).strip() for v in value if str(v).strip()]


class ClinicalPatientContext(BaseModel):
    age_years: float | None = None
    weight_kg: float | None = None
    disease: str | None = None
    route: str | None = None
    crcl_ml_min: float | None = None
    gene_symbol: str
    variants: list[str]


class ClinicalSummary(BaseModel):
    medicines_requested: int
    medicines_resolved: int
    ddi_status: str
    highest_ddi_severity: str | None = None
    known_interactions: int
    predicted_interactions: int
    dosage_rules_found_for: int
    renal_adjustments_found_for: int
    pgx_relevant_for: int
    pgx_variant_matches_for: int
    alternatives_evaluated_for: int
    attention_level: str
    review_flags: list[str]
    narrative: list[str]


class ClinicalAnalyzeResponse(BaseModel):
    status: str
    patient_context: ClinicalPatientContext
    medicine_resolutions: list[MedicineResolutionResponse]
    ddi_status: str
    ddi_analysis: DDICheckResponse | None = None
    dosage_analyses: list[DosageCheckResponse]
    pgx_analyses: list[PGxCheckResponse]
    alternatives_status: str
    alternative_analyses: list[AlternativeRecommendResponse]
    summary: ClinicalSummary
    warnings: list[str]
    disclaimer: str
