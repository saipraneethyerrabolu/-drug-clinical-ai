from __future__ import annotations

from dataclasses import dataclass
import math
import pandas as pd

from app.core.normalization import normalize_text, extract_also_known_as
from app.loaders.drug_loader import load_drugs, load_aliases
from app.loaders.product_loader import load_products, load_product_ingredients


def _clean(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text if text and text.lower() != "nan" else None


@dataclass
class MedicineMappingService:
    def __post_init__(self):
        self.products = load_products()
        self.ingredients = load_product_ingredients()
        self.drugs = load_drugs()
        self.aliases = load_aliases()

        self.products["_norm"] = self.products["normalized_name"].fillna(
            self.products["product_name"].map(normalize_text)
        )
        self.drugs["_norm"] = self.drugs["normalized_name"].fillna(
            self.drugs["name"].map(normalize_text)
        )
        self.aliases["_norm"] = self.aliases["normalized_alias"].fillna(
            self.aliases["alias"].map(normalize_text)
        )

        self._drug_by_norm = {
            row["_norm"]: row for _, row in self.drugs.dropna(subset=["_norm"]).iterrows()
        }
        self._alias_to_drug = {}
        for _, row in self.aliases.iterrows():
            cid = _clean(row.get("canonical_drug_id"))
            norm = _clean(row.get("_norm"))
            if cid and norm:
                drug_rows = self.drugs[self.drugs["canonical_drug_id"] == cid]
                if not drug_rows.empty:
                    self._alias_to_drug[norm] = drug_rows.iloc[0]

    def search(self, query: str, limit: int = 10) -> list[dict]:
        norm = normalize_text(query)
        if not norm:
            return []
        exact = self.products[self.products["_norm"] == norm]
        contains = self.products[
            self.products["_norm"].str.contains(norm, regex=False, na=False)
            & ~self.products.index.isin(exact.index)
        ]
        result = pd.concat([exact, contains], ignore_index=True).head(limit)
        return [
            {
                "product_id": str(r["product_id"]),
                "product_name": str(r["product_name"]),
                "generic_name": _clean(r.get("generic_name")),
                "manufacturer": _clean(r.get("manufacturer")),
                "prescription_required": _clean(r.get("prescription_required")),
            }
            for _, r in result.iterrows()
        ]

    def _resolve_drug_name(self, name: str | None):
        norm = normalize_text(name)
        if not norm:
            return None, None
        if norm in self._drug_by_norm:
            return self._drug_by_norm[norm], "EXACT_CANONICAL_NAME"
        if norm in self._alias_to_drug:
            return self._alias_to_drug[norm], "EXACT_ALIAS"
        return None, None

    def _resolve_ingredient_row(self, row: pd.Series) -> dict:
        cid = _clean(row.get("canonical_drug_id"))
        if cid:
            drug_rows = self.drugs[self.drugs["canonical_drug_id"] == cid]
            drug = drug_rows.iloc[0] if not drug_rows.empty else None
            return {
                "ingredient_raw": _clean(row.get("ingredient_raw")),
                "ingredient_normalized": _clean(row.get("ingredient_normalized")),
                "canonical_drug_id": cid,
                "canonical_name": _clean(row.get("canonical_name")) or (_clean(drug.get("name")) if drug is not None else None),
                "drugbank_id": _clean(row.get("drugbank_id")) or (_clean(drug.get("drugbank-id")) if drug is not None else None),
                "ddinter_id": _clean(row.get("ddinter_id")) or (_clean(drug.get("ddinter_id")) if drug is not None else None),
                "mapping_method": _clean(row.get("mapping_method")) or "DATASET_MAPPING",
                "mapping_status": "RESOLVED",
            }

        ingredient_name = _clean(row.get("ingredient_raw"))
        drug, method = self._resolve_drug_name(ingredient_name)

        # Useful fallback for records like "Paracetamol ... Also Known As: Acetaminophen".
        if drug is None:
            for aka in extract_also_known_as(_clean(row.get("generic_raw"))):
                drug, _ = self._resolve_drug_name(aka)
                if drug is not None:
                    method = "GENERIC_ALSO_KNOWN_AS"
                    break

        if drug is None:
            return {
                "ingredient_raw": ingredient_name,
                "ingredient_normalized": _clean(row.get("ingredient_normalized")) or normalize_text(ingredient_name),
                "canonical_drug_id": None,
                "canonical_name": None,
                "drugbank_id": None,
                "ddinter_id": None,
                "mapping_method": "UNRESOLVED",
                "mapping_status": "UNRESOLVED",
            }

        return {
            "ingredient_raw": ingredient_name,
            "ingredient_normalized": _clean(row.get("ingredient_normalized")) or normalize_text(ingredient_name),
            "canonical_drug_id": _clean(drug.get("canonical_drug_id")),
            "canonical_name": _clean(drug.get("name")),
            "drugbank_id": _clean(drug.get("drugbank-id")),
            "ddinter_id": _clean(drug.get("ddinter_id")),
            "mapping_method": method or "RESOLVED",
            "mapping_status": "RESOLVED",
        }

    def resolve(self, medicine_name: str) -> dict:
        norm = normalize_text(medicine_name)
        exact = self.products[self.products["_norm"] == norm]
        if not exact.empty:
            product = exact.iloc[0]
            match_method = "EXACT_NORMALIZED_PRODUCT_NAME"
        else:
            starts = self.products[self.products["_norm"].str.startswith(norm, na=False)]
            if starts.empty:
                return {
                    "input_name": medicine_name,
                    "product_id": None,
                    "product_name": None,
                    "normalized_product_name": norm,
                    "generic_name": None,
                    "product_match_method": "NOT_FOUND",
                    "mapping_status": "PRODUCT_NOT_FOUND",
                    "ingredients": [],
                }
            product = starts.iloc[0]
            match_method = "PREFIX_NORMALIZED_PRODUCT_NAME"

        product_id = str(product["product_id"])
        ingredient_rows = self.ingredients[self.ingredients["product_id"] == product_id]
        resolved_ingredients = [self._resolve_ingredient_row(r) for _, r in ingredient_rows.iterrows()]
        if not resolved_ingredients:
            status = "NO_INGREDIENT_DATA"
        elif all(x["mapping_status"] == "RESOLVED" for x in resolved_ingredients):
            status = "RESOLVED"
        elif any(x["mapping_status"] == "RESOLVED" for x in resolved_ingredients):
            status = "PARTIALLY_RESOLVED"
        else:
            status = "UNRESOLVED"

        return {
            "input_name": medicine_name,
            "product_id": product_id,
            "product_name": _clean(product.get("product_name")),
            "normalized_product_name": _clean(product.get("normalized_name")) or norm,
            "generic_name": _clean(product.get("generic_name")),
            "product_match_method": match_method,
            "mapping_status": status,
            "ingredients": resolved_ingredients,
        }
