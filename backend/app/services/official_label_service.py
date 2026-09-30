from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class OfficialLabelService:
    """Small openFDA drug-label lookup.

    Returns the official label's `dosage_and_administration` text (as
    published by the manufacturer/FDA) alongside indication and dosage-form
    metadata. This is reference text from the official label only — it is
    not a personalized dosing recommendation and should be presented to
    users as such.
    """

    base_url: str = "https://api.fda.gov/drug/label.json"
    timeout_seconds: float = 8.0
    dosage_text_limit: int = 4000  # dosage sections can be long; give them more room than other fields

    @staticmethod
    def _first_text(value: Any, limit: int = 1400) -> str | None:
        if value is None:
            return None
        if isinstance(value, list):
            value = next((x for x in value if str(x).strip()), None)
        if value is None:
            return None
        text = " ".join(str(value).split())
        if not text:
            return None
        if len(text) > limit:
            text = text[: limit - 1].rstrip() + "…"
        return text

    @staticmethod
    def _join_openfda(values: Any) -> str | None:
        if not values:
            return None
        if not isinstance(values, list):
            values = [values]
        cleaned = []
        for value in values:
            text = str(value).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return ", ".join(cleaned) or None

    def _search(self, field: str, medicine_name: str) -> dict | None:
        query_name = medicine_name.replace('"', ' ').strip()
        if not query_name:
            return None
        params = {
            "search": f'{field}:"{query_name}"',
            "limit": 1,
        }
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = client.get(self.base_url, params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        return results[0] if results else None

    def lookup(self, medicine_name: str) -> dict:
        medicine_name = str(medicine_name or "").strip()
        warnings: list[str] = []
        if not medicine_name:
            return {
                "medicine_name": medicine_name,
                "status": "INVALID_MEDICINE_NAME",
                "source": "FDA Drug Labeling (openFDA)",
                "indication": None,
                "route": None,
                "dosage_form_strength": None,
                "dosage_and_administration_available": False,
                "dosage_and_administration_text": None,
                "source_url": "https://open.fda.gov/apis/drug/label/",
                "warnings": ["A medicine name is required for official-label lookup."],
            }

        result = None
        matched_field = None
        try:
            for field in ("openfda.generic_name", "openfda.brand_name", "openfda.substance_name"):
                result = self._search(field, medicine_name)
                if result:
                    matched_field = field
                    break
        except (httpx.HTTPError, ValueError) as exc:
            return {
                "medicine_name": medicine_name,
                "status": "OFFICIAL_LABEL_LOOKUP_UNAVAILABLE",
                "source": "FDA Drug Labeling (openFDA)",
                "indication": None,
                "route": None,
                "dosage_form_strength": None,
                "dosage_and_administration_available": False,
                "dosage_and_administration_text": None,
                "source_url": "https://open.fda.gov/apis/drug/label/",
                "warnings": [f"Official label lookup could not be completed: {type(exc).__name__}."],
            }

        if not result:
            return {
                "medicine_name": medicine_name,
                "status": "OFFICIAL_LABEL_NOT_FOUND",
                "source": "FDA Drug Labeling (openFDA)",
                "indication": None,
                "route": None,
                "dosage_form_strength": None,
                "dosage_and_administration_available": False,
                "dosage_and_administration_text": None,
                "source_url": "https://open.fda.gov/apis/drug/label/",
                "warnings": ["No matching official FDA drug-label record was found for this medicine name."],
            }

        openfda = result.get("openfda") or {}

        indication = self._first_text(result.get("indications_and_usage"))

        dosage_form_strength = self._first_text(result.get("dosage_forms_and_strengths"))

        route = self._join_openfda(openfda.get("route"))

        # Dosage & Administration section, as published on the official label.
        dosage_section = result.get("dosage_and_administration")
        dosage_text = self._first_text(dosage_section, limit=self.dosage_text_limit)
        dosing_available = bool(dosage_text)

        if not indication:
            warnings.append("The matched label did not expose an Indications and Usage section through openFDA.")
        if not dosage_form_strength:
            warnings.append("The matched label did not expose a Dosage Forms and Strengths section through openFDA.")
        if not dosage_text:
            warnings.append("The matched label did not expose a Dosage and Administration section through openFDA.")
        else:
            warnings.append(
                "Dosage and Administration text is reproduced verbatim from the official FDA label and is not a "
                "personalized recommendation — verify against the current label and clinical judgment before use."
            )

        return {
            "medicine_name": medicine_name,
            "status": "OFFICIAL_LABEL_FOUND",
            "source": "FDA Drug Labeling (openFDA)",
            "indication": indication,
            "route": route,
            "dosage_form_strength": dosage_form_strength,
            "dosage_and_administration_available": dosing_available,
            "dosage_and_administration_text": dosage_text,
            "matched_search_field": matched_field,
            "source_url": "https://open.fda.gov/apis/drug/label/",
            "warnings": warnings,
        }