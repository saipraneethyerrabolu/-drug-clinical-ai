from app.core.config import STANDARD_DOSAGE_FILE, DISEASE_DOSAGE_FILE, RENAL_DOSAGE_FILE
from app.loaders.csv_loader import load_csv


def load_standard_dosage():
    return load_csv(str(STANDARD_DOSAGE_FILE)).copy()


def load_disease_dosage():
    return load_csv(str(DISEASE_DOSAGE_FILE)).copy()


def load_renal_dosage():
    return load_csv(str(RENAL_DOSAGE_FILE)).copy()
