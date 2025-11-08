from fastapi import Header, HTTPException, status
from .account_registry import parse_account_header

ACCOUNT_HEADER = "X-PLM-Account"


def require_account_context(account_header: str = Header(None, alias=ACCOUNT_HEADER)):
    context = parse_account_header(account_header)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account non valido o intestazione mancante",
        )
    return context
