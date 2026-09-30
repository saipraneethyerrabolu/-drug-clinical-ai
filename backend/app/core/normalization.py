import re
import unicodedata


def normalize_text(value: str | None) -> str:
    """Normalize medicine/drug text for deterministic lookup."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_also_known_as(generic_raw: str | None) -> list[str]:
    """Extract names after 'Also Known As:' from product generic text."""
    if not generic_raw:
        return []
    match = re.search(r"also\s+known\s+as\s*:\s*(.+)$", str(generic_raw), flags=re.I)
    if not match:
        return []
    tail = match.group(1)
    values = re.split(r"[,;/|]", tail)
    return [v.strip() for v in values if v.strip()]
