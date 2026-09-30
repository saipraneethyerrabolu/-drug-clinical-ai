from functools import lru_cache
from pathlib import Path
import pandas as pd


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    return pd.read_csv(path, low_memory=False)


@lru_cache(maxsize=None)
def load_csv(path: str) -> pd.DataFrame:
    return _read_csv(Path(path))
