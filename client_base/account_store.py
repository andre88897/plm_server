import base64
import json
from pathlib import Path
from typing import Dict, Optional

CONFIG_DIR = Path.home() / ".plm_client"
CONFIG_FILE = CONFIG_DIR / "account.json"
DEFAULT_CONFIG = {"account": None, "font_scale": 1.0, "credentials": None}


def _read_config() -> Dict:
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return dict(DEFAULT_CONFIG)
    except json.JSONDecodeError:
        return dict(DEFAULT_CONFIG)

    if isinstance(data, dict):
        if "account" not in data and {"stabilimento", "gruppo", "account"} <= data.keys():
            data = {"account": data, "font_scale": 1.0, "credentials": None}
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged
    return dict(DEFAULT_CONFIG)


def _write_config(config: Dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "account": config.get("account"),
        "font_scale": config.get("font_scale", DEFAULT_CONFIG["font_scale"]),
        "credentials": config.get("credentials"),
    }
    with CONFIG_FILE.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)


def load_account_context() -> Optional[Dict[str, str]]:
    config = _read_config()
    account = config.get("account")
    if not isinstance(account, dict):
        return None
    required = {"stabilimento", "gruppo", "account"}
    if not required <= set(account.keys()):
        return None
    return {
        "stabilimento": str(account["stabilimento"]),
        "gruppo": str(account["gruppo"]),
        "account": str(account["account"]),
    }


def save_account_context(context: Dict[str, str]) -> None:
    config = _read_config()
    config["account"] = {
        "stabilimento": context.get("stabilimento"),
        "gruppo": context.get("gruppo"),
        "account": context.get("account"),
    }
    _write_config(config)


def clear_account_context() -> None:
    config = _read_config()
    config["account"] = None
    config["credentials"] = None
    _write_config(config)


def load_font_scale() -> float:
    config = _read_config()
    try:
        scale = float(config.get("font_scale", DEFAULT_CONFIG["font_scale"]))
    except (TypeError, ValueError):
        return DEFAULT_CONFIG["font_scale"]
    return max(0.8, min(1.4, scale))


def save_font_scale(scale: float) -> None:
    config = _read_config()
    config["font_scale"] = max(0.8, min(1.4, float(scale)))
    _write_config(config)


def save_account_password(password: str) -> None:
    config = _read_config()
    if password:
        encoded = base64.b64encode(password.encode("utf-8")).decode("ascii")
        config["credentials"] = {"password_b64": encoded}
    else:
        config["credentials"] = None
    _write_config(config)


def load_account_password() -> Optional[str]:
    config = _read_config()
    creds = config.get("credentials") or {}
    encoded = creds.get("password_b64")
    if not encoded:
        return None
    try:
        return base64.b64decode(encoded.encode("ascii")).decode("utf-8")
    except Exception:
        return None
