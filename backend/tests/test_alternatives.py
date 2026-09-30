from app.services.alternative_service import AlternativeService


def test_known_product_returns_alternatives():
    service = AlternativeService()
    result = service.recommend("augmentin 625 duo tablet", max_alternatives=3)
    assert result["status"] == "ALTERNATIVES_FOUND"
    assert result["candidates_returned"] == 3
    assert result["alternatives"][0]["alternative_product_name"]


def test_ddi_recheck_runs_with_other_medicine():
    service = AlternativeService()
    result = service.recommend(
        "augmentin 625 duo tablet",
        other_medicines=["ADDTREX 50 Tablet 10's"],
        max_alternatives=2,
        use_gnn_fallback=False,
    )
    assert result["status"] == "ALTERNATIVES_FOUND"
    assert all(x["ddi_recheck_status"] == "RECHECK_COMPLETED" for x in result["alternatives"])


def test_no_other_medicine_skips_ddi():
    service = AlternativeService()
    result = service.recommend("azithral 500 tablet", max_alternatives=1)
    assert result["alternatives"][0]["ddi_recheck_status"] == "NOT_RUN_NO_OTHER_MEDICINES"
    assert result["alternatives"][0]["recommendation_class"] == "NOT_ASSESSABLE_NO_COMPARISON_MEDICINES"


def test_unknown_source_safe_response():
    service = AlternativeService()
    result = service.recommend("definitely not a real product xyz", max_alternatives=2)
    assert result["status"] in {"SOURCE_MEDICINE_NOT_RESOLVED", "NO_ALTERNATIVES_FOUND"}
