import pandas as pd
from app.core.config import DRUGS_FILE, ALIASES_FILE
from app.loaders.csv_loader import load_csv


def load_drugs() -> pd.DataFrame:
    return load_csv(str(DRUGS_FILE)).copy()


def load_aliases() -> pd.DataFrame:
    return load_csv(str(ALIASES_FILE)).copy()
