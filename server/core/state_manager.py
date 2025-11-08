from pathlib import Path
from typing import Dict, List

STATE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "state_config.txt"

DEFAULT_STATES = [
    ("concept", "#3498db"),
    ("prototipo", "#1abc9c"),
    ("industrializzato", "#2ecc71"),
    ("solo per ricambi", "#f1c40f"),
    ("morto", "#e74c3c"),
]


def _ensure_config_exists() -> None:
    if STATE_CONFIG_PATH.exists():
        return
    lines = ["# nome_stato,colore_hex"] + [f"{name},{color}" for name, color in DEFAULT_STATES]
    STATE_CONFIG_PATH.write_text("\n".join(lines), encoding="utf-8")


def load_states() -> List[Dict[str, str]]:
    _ensure_config_exists()
    states: List[Dict[str, str]] = []
    raw = STATE_CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    for line in raw:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if not parts:
            continue
        name = parts[0]
        color = parts[1] if len(parts) > 1 and parts[1] else "#777777"
        states.append({"name": name, "color": color})
    if states:
        return states
    return [{"name": name, "color": color} for name, color in DEFAULT_STATES]


def resolve_state(state_name: str | None) -> str:
    if not state_name:
        return DEFAULT_STATES[0][0]
    name = state_name.strip().lower()
    for entry in load_states():
        if entry["name"].lower() == name:
            return entry["name"]
    return DEFAULT_STATES[0][0]


def state_color_map() -> Dict[str, str]:
    return {entry["name"].lower(): entry["color"] for entry in load_states()}


def state_order_map() -> Dict[str, int]:
    return {entry["name"].lower(): idx for idx, entry in enumerate(load_states())}
