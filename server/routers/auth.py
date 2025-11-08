from typing import List

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core import models, database
from core.account_registry import account_hierarchy, find_account, create_account
from core.password_policy import load_policy, validate_password
from core.password_utils import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


class HierarchyGroup(BaseModel):
    nome: str
    accounts: List[str]


class HierarchyNode(BaseModel):
    stabilimento: str
    gruppi: List[HierarchyGroup]


class PasswordPolicyResponse(BaseModel):
    min_length: int
    require_digit: bool
    require_symbol: bool
    require_upper: bool


class LoginPayload(BaseModel):
    stabilimento: str
    gruppo: str
    account: str
    password: str


class AccountInfo(BaseModel):
    stabilimento: str
    gruppo: str
    account: str


class AccountCreatePayload(BaseModel):
    account: str
    password: str


def _upsert_password(db: Session, account: str, password: str) -> None:
    hashed = hash_password(password)
    cred = db.query(models.AccountCredential).filter(models.AccountCredential.account == account).first()
    if cred:
        cred.password_hash = hashed
    else:
        cred = models.AccountCredential(account=account, password_hash=hashed)
        db.add(cred)
    db.commit()


def _get_credential(db: Session, account: str) -> models.AccountCredential | None:
    return db.query(models.AccountCredential).filter(models.AccountCredential.account == account).first()


@router.get("/accounts", response_model=List[HierarchyNode])
def lista_account():
    return account_hierarchy()


@router.get("/policy", response_model=PasswordPolicyResponse)
def password_policy():
    policy = load_policy()
    return PasswordPolicyResponse(**policy)


@router.post("/login", response_model=AccountInfo)
def login_account(payload: LoginPayload, db: Session = Depends(database.get_db)):
    info = find_account(payload.account, payload.stabilimento, payload.gruppo)
    if not info:
        raise HTTPException(status_code=404, detail="Account non trovato")
    cred = _get_credential(db, payload.account)
    if not cred or not verify_password(payload.password, cred.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password non valida")
    return info


@router.post("/accounts", response_model=AccountInfo, status_code=201)
def crea_account(payload: AccountCreatePayload, db: Session = Depends(database.get_db)):
    errors = validate_password(payload.password)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))
    try:
        info = create_account(payload.account)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _upsert_password(db, info["account"], payload.password)
    return info
