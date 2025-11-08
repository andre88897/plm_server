from pathlib import Path
from typing import List, Dict

FORM_CONFIG_PATH = Path(__file__).resolve().parent.parent / "form_config.txt"

DEFAULT_FIELDS = [
    ("descrizione", "Descrizione"),
    ("quantita", "Quantità"),
    ("ubicazione", "Ubicazione"),
]


def _ensure_config_exists() -> None:
    if FORM_CONFIG_PATH.exists():
        return
    lines = ["# nome,label"] + [f"{name},{label}" for name, label in DEFAULT_FIELDS]
    FORM_CONFIG_PATH.write_text("\n".join(lines), encoding="utf-8")


def load_form_fields() -> List[Dict[str, str]]:
    _ensure_config_exists()
    raw_lines = FORM_CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    fields: List[Dict[str, str]] = []
    for idx, line in enumerate(raw_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = [part.strip() for part in stripped.split(",", 1)]
        if not parts:
            continue
        name = parts[0]
        label = parts[1] if len(parts) > 1 and parts[1] else name.title()
        if not name:
            continue
        fields.append({"name": name, "label": label, "order": idx})
    if fields:
        return fields
    return [{"name": name, "label": label, "order": pos} for pos, (name, label) in enumerate(DEFAULT_FIELDS)]
