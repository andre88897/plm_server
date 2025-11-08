from typing import Optional

from . import models, database


def log_activity(
    account_ctx: Optional[dict],
    action: str,
    riferimento: Optional[str] = None,
    dettagli: Optional[str] = None,
) -> None:
    if not account_ctx or not action:
        return
    payload = models.AttivitaLog(
        account=account_ctx.get("account"),
        stabilimento=account_ctx.get("stabilimento"),
        gruppo=account_ctx.get("gruppo"),
        azione=action,
        riferimento=riferimento,
        dettagli=dettagli or "",
    )
    with database.SessionLocal() as session:
        session.add(payload)
        session.commit()
