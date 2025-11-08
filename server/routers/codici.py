from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from core import models, database
from core.state_manager import resolve_state, state_color_map
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from core.auth_context import require_account_context
from core.activity_logger import log_activity

router = APIRouter(prefix="/codici", tags=["Codici"])

# Schema Pydantic per input/output
class CodiceBase(BaseModel):
    codice: str
    descrizione: str
    quantita: float
    ubicazione: str

    model_config = {"from_attributes": True}


class CodiceCreate(CodiceBase):
    stato: Optional[str] = None
    rilascia_subito: bool = False


class CertificazioneOut(BaseModel):
    nome: str
    valore: Optional[str] = None
    ordine: int = 0


class RevisioneFileInfo(BaseModel):
    filename: str
    mimetype: Optional[str] = None
    uploaded_at: Optional[datetime] = None


class RevisioneOut(BaseModel):
    indice: int
    stato: str
    color: str
    cad_file: Optional[str] = None
    is_released: bool
    released_at: Optional[datetime] = None
    certificazione: List[CertificazioneOut]
    files: List[RevisioneFileInfo] = []


class FileInfo(BaseModel):
    filename: str
    uploaded_at: Optional[datetime] = None
    filetype: Optional[str] = None


class CodiceDetail(CodiceBase):
    revisioni: List[RevisioneOut]
    files: List[FileInfo]


@router.post("/", response_model=CodiceBase)
def crea_codice(
    codice: CodiceCreate,
    db: Session = Depends(database.get_db),
    account_ctx: dict = Depends(require_account_context),
):
    """
    Crea un nuovo codice PLM:
    - L'utente specifica solo il tipo (2 cifre iniziali)
    - Il numero progressivo (6 cifre) è globale
    - L'ultima lettera è di controllo (A-Z)
    """
    tipo = codice.codice.strip()
    if len(tipo) != 2 or not tipo.isdigit():
        raise HTTPException(status_code=400, detail="Il tipo deve contenere solo 2 cifre (es. '03')")

    # 🔹 Trova il numero massimo valido in tutti i codici esistenti
    max_num = 0
    tutti = db.query(models.Codice).all()
    for c in tutti:
        try:
            if len(c.codice) >= 8 and c.codice[2:8].isdigit():
                n = int(c.codice[2:8])
                if n > max_num:
                    max_num = n
        except Exception:
            # ignora codici non validi
            continue

    numero = max_num + 1
    numero_str = f"{numero:06d}"

    # 🔹 Calcola lettera di controllo
    base = f"{tipo}{numero_str}"
    checksum = sum(ord(ch) for ch in base) % 26
    lettera = chr(ord('A') + checksum)

    nuovo_codice = f"{base}{lettera}"

    # 🔹 Crea il nuovo record
    db_codice = models.Codice(
        codice=nuovo_codice,
        descrizione=(codice.descrizione or "").strip(),
        quantita=codice.quantita,
        ubicazione=(codice.ubicazione or "").strip()
    )

    db.add(db_codice)
    db.commit()
    db.refresh(db_codice)

    stato = resolve_state(codice.stato)
    revisione = models.Revisione(
        codice_id=db_codice.id,
        indice=0,
        stato=stato,
        cad_file=None,
        is_released=bool(codice.rilascia_subito),
        released_at=func.now() if codice.rilascia_subito else None,
    )
    db.add(revisione)
    db.commit()
    db.refresh(db_codice)

    log_activity(account_ctx, "codice_creato", riferimento=nuovo_codice)
    return db_codice


@router.get("/", response_model=List[CodiceBase])
def lista_codici(include_unreleased: bool = False, db: Session = Depends(database.get_db)):
    query = db.query(models.Codice)
    if not include_unreleased:
        query = query.join(models.Revisione).filter(models.Revisione.is_released.is_(True)).distinct()
    return query.all()


@router.get("/{codice}", response_model=CodiceBase)
def leggi_codice(codice: str, include_unreleased: bool = False, db: Session = Depends(database.get_db)):
    db_codice = db.query(models.Codice).filter(models.Codice.codice == codice).first()
    if not db_codice:
        raise HTTPException(status_code=404, detail="Codice non trovato")
    if not include_unreleased:
        released = any(rev.is_released for rev in db_codice.revisioni)
        if not released:
            raise HTTPException(status_code=404, detail="Codice non rilasciato")
    return db_codice


@router.get("/{codice}/dettaglio", response_model=CodiceDetail)
def dettaglio_codice(codice: str, include_unreleased: bool = False, db: Session = Depends(database.get_db)):
    codice_obj = db.query(models.Codice).filter(models.Codice.codice == codice).first()
    if not codice_obj:
        raise HTTPException(status_code=404, detail="Codice non trovato")

    if not codice_obj.revisioni:
        default_state = resolve_state(None)
        db_rev = models.Revisione(codice_id=codice_obj.id, indice=0, stato=default_state)
        db.add(db_rev)
        db.commit()
        db.refresh(codice_obj)
    elif not include_unreleased:
        has_release = any(rev.is_released for rev in codice_obj.revisioni)
        if not has_release:
            raise HTTPException(status_code=404, detail="Codice non rilasciato")

    color_map = state_color_map()

    revisioni = [
        RevisioneOut(
            indice=rev.indice,
            stato=rev.stato,
            color=color_map.get(rev.stato.lower(), "#777777"),
            cad_file=rev.cad_file,
            is_released=rev.is_released,
            released_at=rev.released_at,
            certificazione=[
                CertificazioneOut(nome=campo.nome, valore=campo.valore, ordine=campo.ordine)
                for campo in rev.certificazione
            ],
            files=[
                RevisioneFileInfo(
                    filename=f.filename,
                    mimetype=f.mimetype,
                    uploaded_at=f.uploaded_at,
                )
                for f in rev.files
            ],
        )
        for rev in codice_obj.revisioni
    ]

    files = [
        FileInfo(
            filename=f.filename,
            uploaded_at=f.uploaded_at,
            filetype=f.filetype,
        )
        for f in codice_obj.files
    ]

    return CodiceDetail(
        codice=codice_obj.codice,
        descrizione=codice_obj.descrizione,
        quantita=codice_obj.quantita,
        ubicazione=codice_obj.ubicazione,
        revisioni=revisioni,
        files=files,
    )
