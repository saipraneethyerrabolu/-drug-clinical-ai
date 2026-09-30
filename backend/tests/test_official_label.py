from app.services.official_label_service import OfficialLabelService


def test_official_label_parses_non_actionable_metadata(monkeypatch):
    service = OfficialLabelService()

    sample = {
        "indications_and_usage": ["Used for an example approved indication."],
        "dosage_forms_and_strengths": ["Tablet, 50 mg."],
        "dosage_and_administration": ["Actionable dosing text intentionally not returned."],
        "openfda": {"route": ["ORAL"]},
    }

    monkeypatch.setattr(service, "_search", lambda field, medicine_name: sample)
    result = service.lookup("ExampleDrug")

    assert result["status"] == "OFFICIAL_LABEL_FOUND"
    assert result["route"] == "ORAL"
    assert result["dosage_form_strength"] == "Tablet, 50 mg."
    assert result["dosage_and_administration_available"] is True
    assert "dosage_and_administration" not in result


def test_official_label_not_found(monkeypatch):
    service = OfficialLabelService()
    monkeypatch.setattr(service, "_search", lambda field, medicine_name: None)
    result = service.lookup("MissingDrug")
    assert result["status"] == "OFFICIAL_LABEL_NOT_FOUND"
