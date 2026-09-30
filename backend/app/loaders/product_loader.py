import pandas as pd
from app.core.config import PRODUCTS_FILE, PRODUCT_INGREDIENTS_FILE
from app.loaders.csv_loader import load_csv


def load_products() -> pd.DataFrame:
    return load_csv(str(PRODUCTS_FILE)).copy()


def load_product_ingredients() -> pd.DataFrame:
    return load_csv(str(PRODUCT_INGREDIENTS_FILE)).copy()
