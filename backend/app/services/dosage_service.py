from __future__ import annotations

from dataclasses import dataclass
import math
import pandas as pd

from app.core.normalization import normalize_text
from app.loaders.dosage_loader import (
    load_standard_dosage,
    load_disease_dosage,
    load_renal_dosage,
)
from app.services.medicine_mapping_service import MedicineMappingService


def _clean(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text if text and text.lower() != "nan" else None


def _num(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _in_range(value: float | None, low, high) -> bool:
    if value is None:
        return True
    lo, hi = _num(low), _num(high)
    if lo is not None and value < lo:
        return False
    if hi is not None and value > hi:
        return False
    return True


def _age_matches(row, age_years: float | None) -> bool:
    if age_years is None:
        return True
    # Convert the single user age into all units represented by the source data.
    age_months = age_years * 12.0
    age_days = age_years * 365.25
    constraints = [
        (_num(row.get("min_age_y")), _num(row.get("max_age_y")), age_years),
        (_num(row.get("min_age_m")), _num(row.get("max_age_m")), age_months),
        (_num(row.get("min_age_d")), _num(row.get("max_age_d")), age_days),
    ]
    # A row can express age in one or more unit systems. Every represented
    # constraint must match; absent constraint columns do not restrict the row.
    for lo, hi, value in constraints:
        if lo is None and hi is None:
            continue
        if lo is not None and value < lo:
            return False
        if hi is not None and value > hi:
            return False
    return True


def _canonical_ids_from_cell(value) -> set[str]:
    text = _clean(value)
    if not text:
        return set()
    # Unified data normally stores one ID, but support common delimiters safely.
    for sep in ["|", ";", ","]:
        text = text.replace(sep, " ")
    return {x.strip() for x in text.split() if x.strip().startswith("DRUG")}


def _dose_fields(row) -> dict:
    names = [
        "min_dose_dw_mg", "max_dose_dw_mg", "min_dose_dw_iu", "max_dose_dw_iu",
        "limit_mg", "limit_iu", "min_dose_dd_mg", "max_dose_dd_mg",
        "min_dose_dd_UNIT", "max_dose_dd_iu",
    ]
    result = {}
    for name in names:
        if name in row:
            value = _num(row.get(name))
            if value is not None:
                result[name] = value
    return result


def _renal_dose_fields(row) -> dict:
    names = ["max_dose_dd_mg", "max_dose_dw_mg", "max_dose_dd_iu", "max_dose_dw_iu"]
    return {name: _num(row.get(name)) for name in names if _num(row.get(name)) is not None}


@dataclass
class DosageService:
    mapping_service: MedicineMappingService | None = None

    def __post_init__(self):
        self.mapping_service = self.mapping_service or MedicineMappingService()
        self.standard = load_standard_dosage()
        self.disease = load_disease_dosage()
        self.renal = load_renal_dosage()

    def _rows_for_drugs(self, df: pd.DataFrame, canonical_ids: set[str], names: set[str]) -> pd.DataFrame:
        if not canonical_ids and not names:
            return df.iloc[0:0]
        id_mask = df["canonical_drug_ids"].map(
            lambda v: bool(_canonical_ids_from_cell(v) & canonical_ids)
        ) if "canonical_drug_ids" in df.columns else pd.Series(False, index=df.index)
        name_mask = df["generic_normalized"].fillna("").isin(names) if "generic_normalized" in df.columns else pd.Series(False, index=df.index)
        return df[id_mask | name_mask].copy()

    def _filter_common(self, df: pd.DataFrame, age_years, weight_kg, route) -> pd.DataFrame:
        if df.empty:
            return df
        mask = df.apply(lambda r: _age_matches(r, age_years), axis=1)
        if weight_kg is not None:
            mask &= df.apply(lambda r: _in_range(weight_kg, r.get("min_weight"), r.get("max_weight")), axis=1)
        if route:
            rn = normalize_text(route)
            mask &= df["route"].fillna("").map(normalize_text).eq(rn)
        return df[mask].copy()

    def _format_rule(self, row, rule_type: str) -> dict:
        return {
            "record_id": str(row.get("record_id")),
            "rule_type": rule_type,
            "generic": _clean(row.get("generic")),
            "disease": _clean(row.get("disease")),
            "route": _clean(row.get("route")),
            "age_range": {
                "days": {"min": _num(row.get("min_age_d")), "max": _num(row.get("max_age_d"))},
                "months": {"min": _num(row.get("min_age_m")), "max": _num(row.get("max_age_m"))},
                "years": {"min": _num(row.get("min_age_y")), "max": _num(row.get("max_age_y"))},
            },
            "weight_range_kg": {"min": _num(row.get("min_weight")), "max": _num(row.get("max_weight"))},
            "dose_fields": _dose_fields(row),
            "mapping_status": _clean(row.get("drug_mapping_status")),
        }

    def _format_renal(self, row) -> dict:
        return {
            "record_id": str(row.get("record_id")),
            "generic": _clean(row.get("generic")),
            "disease": _clean(row.get("disease")),
            "route": _clean(row.get("route")),
            "crcl_range_ml_min": {"min": _num(row.get("min_crcl")), "max": _num(row.get("max_crcl"))},
            "weight_range_kg": {"min": _num(row.get("min_weight")), "max": _num(row.get("max_weight"))},
            "dose_fields": _renal_dose_fields(row),
            "flag": _clean(row.get("flag")),
            "mapping_status": _clean(row.get("drug_mapping_status")),
        }

    def check(self, medicine_name: str, age_years=None, weight_kg=None, disease=None, route=None, crcl_ml_min=None) -> dict:
        resolution = self.mapping_service.resolve(medicine_name)
        resolved = [i for i in resolution.get("ingredients", []) if i.get("mapping_status") == "RESOLVED"]
        canonical_ids = {i.get("canonical_drug_id") for i in resolved if i.get("canonical_drug_id")}
        canonical_names = {i.get("canonical_name") for i in resolved if i.get("canonical_name")}
        normalized_names = {normalize_text(n) for n in canonical_names if n}

        warnings: list[str] = []
        if not canonical_ids:
            return {
                "medicine_resolution": resolution,
                "canonical_drug_ids": [],
                "canonical_drug_names": [],
                "status": "MEDICINE_NOT_RESOLVED",
                "selection_strategy": "NO_DOSAGE_LOOKUP",
                "matched_disease": None,
                "matched_route": route,
                "standard_or_disease_rules": [],
                "renal_adjustments": [],
                "warnings": ["The medicine could not be mapped to a canonical drug, so dosage rules were not searched."],
                "disclaimer": "Dataset-backed educational output only; not a prescription or substitute for clinician/pharmacist judgment.",
            }

        standard = self._rows_for_drugs(self.standard, canonical_ids, normalized_names)
        standard = self._filter_common(standard, age_years, weight_kg, route)

        disease_rows = self._rows_for_drugs(self.disease, canonical_ids, normalized_names)
        matched_disease = None
        if disease:
            dn = normalize_text(disease)
            exact_disease = disease_rows[disease_rows["disease"].fillna("").map(normalize_text).eq(dn)]
            exact_disease = self._filter_common(exact_disease, age_years, weight_kg, route)
            if not exact_disease.empty:
                selected = exact_disease
                rule_type = "DISEASE_SPECIFIC"
                matched_disease = disease
                strategy = "DISEASE_SPECIFIC_RULES_PREFERRED"
            else:
                selected = standard
                rule_type = "STANDARD"
                strategy = "STANDARD_FALLBACK_NO_MATCHING_DISEASE_RULE"
                warnings.append("No disease-specific rule matched all supplied filters; standard rules were used when available.")
        else:
            selected = standard
            rule_type = "STANDARD"
            strategy = "STANDARD_RULES_NO_DISEASE_SUPPLIED"

        renal_matches = self._rows_for_drugs(self.renal, canonical_ids, normalized_names)
        if route and not renal_matches.empty:
            rn = normalize_text(route)
            renal_matches = renal_matches[renal_matches["route"].fillna("").map(normalize_text).eq(rn)]
        if weight_kg is not None and not renal_matches.empty:
            renal_matches = renal_matches[renal_matches.apply(lambda r: _in_range(weight_kg, r.get("min_weight"), r.get("max_weight")), axis=1)]
        if disease and not renal_matches.empty and renal_matches["disease"].notna().any():
            dn = normalize_text(disease)
            disease_specific = renal_matches[renal_matches["disease"].fillna("").map(normalize_text).eq(dn)]
            general = renal_matches[renal_matches["disease"].isna()]
            renal_matches = pd.concat([disease_specific, general]).drop_duplicates()
        if crcl_ml_min is not None and not renal_matches.empty:
            renal_matches = renal_matches[renal_matches.apply(lambda r: _in_range(crcl_ml_min, r.get("min_crcl"), r.get("max_crcl")), axis=1)]
        elif crcl_ml_min is None and not renal_matches.empty:
            warnings.append("Renal dosage data exists for this drug, but CrCl was not supplied; renal rules are shown unfiltered by kidney function.")

        if selected.empty:
            status = "NO_MATCHING_DOSAGE_RULE"
            warnings.append("No standard or disease-specific dosage row matched the resolved drug and supplied filters.")
        else:
            status = "DOSAGE_RULES_FOUND"

        if crcl_ml_min is not None and renal_matches.empty:
            warnings.append("No renal adjustment row matched the supplied CrCl and other filters.")

        return {
            "medicine_resolution": resolution,
            "canonical_drug_ids": sorted(canonical_ids),
            "canonical_drug_names": sorted(canonical_names),
            "status": status,
            "selection_strategy": strategy,
            "matched_disease": matched_disease,
            "matched_route": route,
            "standard_or_disease_rules": [self._format_rule(r, rule_type) for _, r in selected.iterrows()],
            "renal_adjustments": [self._format_renal(r) for _, r in renal_matches.iterrows()],
            "warnings": warnings,
            "disclaimer": "Dataset-backed educational output only; not a prescription or substitute for clinician/pharmacist judgment.",
        }
