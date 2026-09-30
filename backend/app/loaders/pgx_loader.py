from app.core.config import DATA_DIR
from app.loaders.csv_loader import load_csv


def load_pgx_genes():
    return load_csv(DATA_DIR / '13_pgx_genes.csv')


def load_pgx_variants():
    return load_csv(DATA_DIR / '14_pgx_variants.csv')


def load_pgx_drug_rules():
    return load_csv(DATA_DIR / '15_pgx_drug_rules.csv')
