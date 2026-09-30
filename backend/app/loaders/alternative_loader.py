import pandas as pd

from app.core.config import ALTERNATIVES_FILE

_ALT_COLS = [
    "alternative_id", "source_product_id", "source_product_name", "substitute_rank",
    "alternative_product_name", "alternative_product_id", "source_canonical_drug_ids",
    "alternative_canonical_drug_ids", "canonical_mapping_status",
]


def find_alternatives(source_product_id: str, limit: int | None = None) -> list[dict]:
    """Stream the 1.15M-row alternatives table instead of keeping it in RAM."""
    found: list[dict] = []
    for chunk in pd.read_csv(ALTERNATIVES_FILE, usecols=_ALT_COLS, chunksize=100_000):
        hit = chunk[chunk["source_product_id"] == source_product_id]
        if not hit.empty:
            found.extend(hit.to_dict(orient="records"))
    found.sort(key=lambda r: (pd.isna(r.get("substitute_rank")), r.get("substitute_rank") if not pd.isna(r.get("substitute_rank")) else 999999))
    return found[:limit] if limit else found
