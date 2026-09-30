import pandas as pd

from app.core.config import INTERACTIONS_FILE
from app.loaders.csv_loader import load_csv


def load_interactions() -> pd.DataFrame:
    """Load the unified DDInter interaction table."""
    return load_csv(str(INTERACTIONS_FILE)).copy()
