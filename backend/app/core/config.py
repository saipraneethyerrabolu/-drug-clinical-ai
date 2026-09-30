from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR.parent / "models"

DRUGS_FILE = DATA_DIR / "01_drugs.csv"
ALIASES_FILE = DATA_DIR / "02_drug_aliases.csv"
PRODUCTS_FILE = DATA_DIR / "03_products.csv"
PRODUCT_INGREDIENTS_FILE = DATA_DIR / "04_product_ingredients.csv"
INTERACTIONS_FILE = DATA_DIR / "07_interactions.csv"
ALTERNATIVES_FILE = DATA_DIR / "08_alternatives.csv"

# Optional Phase 2+ model artifact. The DDI module works without this file by
# returning deterministic dataset-backed results and an explicit model status.
DDI_MODEL_FILE = MODELS_DIR / "ddi_best_model.pt"

STANDARD_DOSAGE_FILE = DATA_DIR / "09_standard_dosage.csv"
DISEASE_DOSAGE_FILE = DATA_DIR / "10_disease_dosage.csv"
RENAL_DOSAGE_FILE = DATA_DIR / "11_renal_dosage.csv"
