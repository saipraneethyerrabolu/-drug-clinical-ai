from app.services.pgx_service import PGxService

svc=PGxService()

def test_azathioprine_tpmt_rule_and_variant():
    r=svc.check("Aretha 50mg Tablet 10'S",'TPMT',['rs1142345'])
    assert r['status']=='PGX_RULE_AND_VARIANT_FOUND'
    assert r['canonical_drug_ids']==['DRUG000977']
    assert r['drug_rules'][0]['drug_name']=='Azathioprine'
    assert r['matched_variants'][0]['rsid']=='rs1142345'

def test_tpmt_rule_without_variant_does_not_infer():
    r=svc.check("Aretha 50mg Tablet 10'S",'TPMT',[])
    assert r['status']=='PGX_RULE_FOUND_NO_VARIANT_SUPPLIED'
    assert r['matched_variants']==[]

def test_nonimplemented_gene_is_explicit():
    r=svc.check("Aretha 50mg Tablet 10'S",'NUDT15',[])
    assert r['status']=='GENE_NOT_IMPLEMENTED'
    assert r['drug_rules']==[]

def test_non_pgx_drug():
    r=svc.check('acil 500mg injection','TPMT',['rs1142345'])
    assert r['status']=='NO_PGX_RULE_FOR_DRUG'
