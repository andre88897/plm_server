import csv
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = BASE_DIR / "accounts.csv"
DEFAULT_STABILIMENTO = "da assegnare"
DEFAULT_GRUPPO = "da assegnare"


def _read_accounts() -> List[Dict[str, str]]:
    if not ACCOUNTS_FILE.exists():
        return []
    with ACCOUNTS_FILE.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            stabilimento = (row.get("stabilimento") or "").strip()
            gruppo = (row.get("gruppo") or "").strip()
            account = (row.get("account") or "").strip()
            if not stabilimento or not gruppo or not account:
                continue
            rows.append(
                {
                    "stabilimento": stabilimento,
                    "gruppo": gruppo,
                    "account": account,
                }
            )
        return rows


def account_hierarchy() -> List[Dict[str, object]]:
    hierarchy: Dict[str, Dict[str, List[str]]] = {}
    for row in _read_accounts():
        stabilimento = row["stabilimento"]
        gruppo = row["gruppo"]
        account = row["account"]
        hierarchy.setdefault(stabilimento, {})
        hierarchy[stabilimento].setdefault(gruppo, [])
        if account not in hierarchy[stabilimento][gruppo]:
            hierarchy[stabilimento][gruppo].append(account)

    result: List[Dict[str, object]] = []
    for stabilimento, groups in sorted(hierarchy.items()):
        gruppi_payload = []
        for group_name, accounts in sorted(groups.items()):
            gruppi_payload.append(
                {
                    "nome": group_name,
                    "accounts": sorted(accounts),
                }
            )
        result.append({"stabilimento": stabilimento, "gruppi": gruppi_payload})
    return result


def find_account(account: str, stabilimento: Optional[str] = None, gruppo: Optional[str] = None) -> Optional[Dict[str, str]]:
    account_lower = (account or "").strip().lower()
    stabilimento_lower = (stabilimento or "").strip().lower() or None
    gruppo_lower = (gruppo or "").strip().lower() or None
    if not account_lower:
        return None

    for row in _read_accounts():
        if row["account"].lower() != account_lower:
            continue
        if stabilimento_lower and row["stabilimento"].lower() != stabilimento_lower:
            continue
        if gruppo_lower and row["gruppo"].lower() != gruppo_lower:
            continue
        return row
    return None


def parse_account_header(raw_value: str) -> Optional[Dict[str, str]]:
    """
    Header format: stabilimento|gruppo|account
    """
    if not raw_value:
        return None
    parts = [p.strip() for p in raw_value.split("|")]
    if len(parts) != 3:
        return None
    stabilimento, gruppo, account = parts
    return find_account(account, stabilimento, gruppo)


def _ensure_accounts_file():
    if ACCOUNTS_FILE.exists():
        return
    ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ACCOUNTS_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["stabilimento", "gruppo", "account"])


def create_account(account: str) -> Dict[str, str]:
    normalized = (account or "").strip()
    if not normalized:
        raise ValueError("Nome account obbligatorio")
    if find_account(normalized):
        raise ValueError("Account già esistente")
    _ensure_accounts_file()
    with ACCOUNTS_FILE.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([DEFAULT_STABILIMENTO, DEFAULT_GRUPPO, normalized])
    return {
        "stabilimento": DEFAULT_STABILIMENTO,
        "gruppo": DEFAULT_GRUPPO,
        "account": normalized,
    }
