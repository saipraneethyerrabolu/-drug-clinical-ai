from __future__ import annotations
import math
from app.loaders.pgx_loader import load_pgx_genes, load_pgx_variants, load_pgx_drug_rules
from app.services.medicine_mapping_service import MedicineMappingService


def _clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s=str(v).strip()
    return None if not s or s.lower()=='nan' else s

def _bool(v):
    if isinstance(v, bool): return v
    if v is None or (isinstance(v,float) and math.isnan(v)): return None
    return str(v).strip().lower() in {'true','1','yes'}

class PGxService:
    def __init__(self, mapping_service: MedicineMappingService | None = None):
        self.mapping = mapping_service or MedicineMappingService()
        self.genes=load_pgx_genes()
        self.variants=load_pgx_variants()
        self.rules=load_pgx_drug_rules()

    def check(self, medicine_name:str, gene_symbol:str='TPMT', variants:list[str]|None=None):
        variants=variants or []
        resolution=self.mapping.resolve(medicine_name)
        ingredients=[x for x in resolution['ingredients'] if x.get('canonical_drug_id')]
        cids=list(dict.fromkeys(x['canonical_drug_id'] for x in ingredients))
        names=list(dict.fromkeys(x['canonical_name'] for x in ingredients if x.get('canonical_name')))
        gene=(gene_symbol or 'TPMT').strip().upper()
        warnings=[]
        if gene != 'TPMT':
            warnings.append('Only TPMT is implemented from the supplied PGx files. Other genes, including NUDT15, are not evaluated.')
            return self._response(resolution,cids,names,'GENE_NOT_IMPLEMENTED',gene,variants,[],[],False,warnings)
        gene_rows=self.genes[self.genes['symbol'].astype(str).str.upper()==gene]
        if gene_rows.empty:
            return self._response(resolution,cids,names,'GENE_NOT_FOUND',gene,variants,[],[],False,['TPMT gene metadata was not found.'])
        gene_id=str(gene_rows.iloc[0]['pgx_gene_id'])
        requested={v.lower() for v in variants}
        matched=[]
        for _,r in self.variants[self.variants['pgx_gene_id']==gene_id].iterrows():
            rsid=_clean(r.get('rsid'))
            allele=_clean(r.get('defining_allele_relationship')) or ''
            if requested and (rsid.lower() in requested or any(v in allele.lower() for v in requested)):
                matched.append({'pgx_variant_id':str(r['pgx_variant_id']),'rsid':rsid,'variant_type':_clean(r.get('variant_type')),'clinical_significance':_clean(r.get('clinical_significance')),'defining_allele_relationship':_clean(r.get('defining_allele_relationship')),'source':_clean(r.get('source'))})
        rule_rows=self.rules[(self.rules['canonical_drug_id'].isin(cids)) & (self.rules['gene_symbol'].astype(str).str.upper()==gene)]
        rules=[]
        for _,r in rule_rows.iterrows():
            rules.append({'pgx_rule_id':str(r['pgx_rule_id']),'canonical_drug_id':str(r['canonical_drug_id']),'drug_name':str(r['drug_name']),'gene_symbol':str(r['gene_symbol']),'guideline_name':_clean(r.get('guideline_name')),'source':_clean(r.get('source')),'dosing_information':_bool(r.get('dosing_information')),'recommendation_available':_bool(r.get('recommendation_available')),'alternate_drug_available':_bool(r.get('alternate_drug_available')),'pediatric_applicable':_bool(r.get('pediatric_applicable')),'recommendation_summary':_clean(r.get('recommendation_summary')),'implementation_scope':_clean(r.get('implementation_scope')),'validation_status':_clean(r.get('validation_status'))})
        if not cids: status='MEDICINE_NOT_RESOLVED'
        elif not rules: status='NO_PGX_RULE_FOR_DRUG'
        elif variants and not matched: status='PGX_RULE_FOUND_VARIANT_NOT_RECOGNIZED'; warnings.append('A TPMT drug rule exists, but none of the supplied variants matched the three variants implemented in this dataset.')
        elif not variants: status='PGX_RULE_FOUND_NO_VARIANT_SUPPLIED'; warnings.append('A TPMT drug rule exists, but no patient variant was supplied; no genotype/phenotype inference was made.')
        else: status='PGX_RULE_AND_VARIANT_FOUND'
        if rules: warnings.append('NUDT15 is mentioned by the CPIC source text but is not implemented from the supplied PGx files.')
        return self._response(resolution,cids,names,status,gene,variants,matched,rules,bool(rules),warnings)

    def _response(self,res,cids,names,status,gene,variants,matched,rules,relevant,warnings):
        return {'medicine_resolution':res,'canonical_drug_ids':cids,'canonical_drug_names':names,'status':status,'gene_symbol':gene,'implementation_scope':'TPMT_ONLY','supplied_variants':variants,'matched_variants':matched,'drug_rules':rules,'pgx_relevant':relevant,'warnings':warnings,'disclaimer':'Dataset-backed educational PGx output only; no genotype-to-phenotype or prescribing decision should be made without validated clinical genetics and clinician/pharmacist review.'}
