from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_standard_dosage_amikacin_adult_iv():
    r = client.post('/api/dosage/check', json={
        'medicine_name': 'acil 500mg injection',
        'age_years': 30,
        'weight_kg': 70,
        'route': 'IV'
    })
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'DOSAGE_RULES_FOUND'
    assert 'DRUG000467' in body['canonical_drug_ids']
    assert any(x['route'] == 'IV' for x in body['standard_or_disease_rules'])


def test_disease_specific_preferred():
    r = client.post('/api/dosage/check', json={
        'medicine_name': 'acil 500mg injection',
        'age_years': 30,
        'weight_kg': 70,
        'disease': 'Bacteremia',
        'route': 'IV'
    })
    assert r.status_code == 200
    body = r.json()
    assert body['selection_strategy'] == 'DISEASE_SPECIFIC_RULES_PREFERRED'
    assert body['standard_or_disease_rules'][0]['rule_type'] == 'DISEASE_SPECIFIC'
    assert body['standard_or_disease_rules'][0]['disease'] == 'Bacteremia'


def test_renal_rule_filtered_by_crcl():
    r = client.post('/api/dosage/check', json={
        'medicine_name': 'acil 500mg injection',
        'age_years': 30,
        'weight_kg': 70,
        'route': 'IV',
        'crcl_ml_min': 55
    })
    assert r.status_code == 200
    body = r.json()
    assert len(body['renal_adjustments']) >= 1
    assert any(x['crcl_range_ml_min']['min'] <= 55 <= x['crcl_range_ml_min']['max'] for x in body['renal_adjustments'])


def test_unresolved_medicine_is_safe():
    r = client.post('/api/dosage/check', json={'medicine_name': 'definitely-not-a-real-product-xyz'})
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'MEDICINE_NOT_RESOLVED'
    assert body['standard_or_disease_rules'] == []
