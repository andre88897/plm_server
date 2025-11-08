import csv
from pathlib import Path
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_FILE = BASE_DIR / "password_policy.csv"

DEFAULT_POLICY = {
    "min_length": 8,
    "require_digit": True,
    "require_symbol": True,
    "require_upper": False,
}


def _bool_value(value: str) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip() in {"1", "true", "yes", "on"}


@lru_cache()
def load_policy() -> dict:
    if not POLICY_FILE.exists():
        return dict(DEFAULT_POLICY)
    with POLICY_FILE.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        policy = dict(DEFAULT_POLICY)
        for row in reader:
            key = (row.get("rule") or "").strip().lower()
            value = (row.get("value") or "").strip()
            if not key:
                continue
            if key == "min_length":
                try:
                    policy["min_length"] = max(1, int(value))
                except ValueError:
                    continue
            elif key == "require_digit":
                policy["require_digit"] = _bool_value(value)
            elif key == "require_symbol":
                policy["require_symbol"] = _bool_value(value)
            elif key == "require_upper":
                policy["require_upper"] = _bool_value(value)
        return policy


def policy_description(policy: dict | None = None) -> str:
    pol = policy or load_policy()
    parts = [f"Lunghezza minima {pol['min_length']}"]
    if pol.get("require_digit"):
        parts.append("almeno una cifra")
    if pol.get("require_symbol"):
        parts.append("almeno un simbolo")
    if pol.get("require_upper"):
        parts.append("almeno una lettera maiuscola")
    return ", ".join(parts)


def validate_password(password: str) -> list[str]:
    pol = load_policy()
    errors = []
    if len(password) < pol["min_length"]:
        errors.append(f"La password deve avere almeno {pol['min_length']} caratteri.")
    if pol.get("require_digit") and not any(ch.isdigit() for ch in password):
        errors.append("La password deve contenere almeno una cifra.")
    symbols = set("!@#$%^&*()-_=+[]{};:,.<>?/\\|`~\"'")
    if pol.get("require_symbol") and not any(ch in symbols for ch in password):
        errors.append("La password deve contenere almeno un simbolo.")
    if pol.get("require_upper") and not any(ch.isupper() for ch in password):
        errors.append("La password deve contenere almeno una lettera maiuscola.")
    return errors
