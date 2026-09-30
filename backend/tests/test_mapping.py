from app.core.normalization import normalize_text
from app.services.medicine_mapping_service import MedicineMappingService


def test_normalization():
    assert normalize_text("Dolo-650 Tablet") == "dolo 650 tablet"


def test_search_dolo():
    service = MedicineMappingService()
    rows = service.search("Dolo 650", limit=10)
    assert rows
    assert any("dolo 650" in r["product_name"].lower() for r in rows)


def test_resolve_known_product():
    service = MedicineMappingService()
    result = service.resolve("1-AL 10 Tablet")
    assert result["mapping_status"] == "RESOLVED"
    assert result["ingredients"][0]["canonical_name"] == "Levocetirizine"
    assert result["ingredients"][0]["drugbank_id"] == "DB06282"


def test_resolve_dolo_650_using_aka_fallback():
    service = MedicineMappingService()
    result = service.resolve("Dolo 650 Tablet 15's")
    assert result["mapping_status"] == "RESOLVED"
    assert result["ingredients"][0]["canonical_name"] == "Acetaminophen"
    assert result["ingredients"][0]["canonical_drug_id"] == "DRUG000306"


def test_unknown_product_is_safe():
    service = MedicineMappingService()
    result = service.resolve("Definitely Not A Real Medicine XYZ123")
    assert result["mapping_status"] == "PRODUCT_NOT_FOUND"
    assert result["ingredients"] == []
