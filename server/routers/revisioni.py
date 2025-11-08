from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import shutil
import uuid

from core import models, database
from core.state_manager import resolve_state, state_color_map, state_order_map
from core.form_manager import load_form_fields
from core.auth_context import require_account_context
from core.activity_logger import log_activity

router = APIRouter(prefix="/revisioni", tags=["Revisioni"])
REV_FILES_DIR = Path("uploaded_files") / "revisioni"
REV_FILES_DIR.mkdir(parents=True, exist_ok=True)


class RevisioneCreate(BaseModel):
    codice: str
    indice: Optional[int] = None
    stato: Optional[str] = None
    cad_file: Optional[str] = None


class RevisioneFilePayload(BaseModel):
    filename: str
    mimetype: Optional[str] = None
    uploaded_at: Optional[str] = None


class RevisioneResponse(BaseModel):
    indice: int
    stato: str
    color: str
    cad_file: Optional[str] = None
    is_released: bool
    released_at: Optional[str] = None
    files: List[RevisioneFilePayload]


class CertCampoBase(BaseModel):
    nome: str
    valore: Optional[str] = None
    ordine: int = 0


class CertCampo(CertCampoBase):
    label: str


class CertPayload(BaseModel):
    campi: List[CertCampoBase]


class ChangeStatePayload(BaseModel):
    stato: str


@router.post("/", response_model=RevisioneResponse)
def crea_revisione(
    payload: RevisioneCreate,
    db: Session = Depends(database.get_db),
    account_ctx: dict = Depends(require_account_context),
):
    codice_obj = db.query(models.Codice).filter_by(codice=payload.codice).first()
    if not codice_obj:
        raise HTTPException(status_code=404, detail="Codice non trovato")

    if any(not rev.is_released for rev in codice_obj.revisioni):
        raise HTTPException(status_code=400, detail="Esiste già una revisione non rilasciata")

    existing_indices = {rev.indice for rev in codice_obj.revisioni}

    if payload.indice is None:
        indice = 0
        if existing_indices:
            indice = max(existing_indices) + 1
    else:
        indice = payload.indice
        if indice in existing_indices:
            raise HTTPException(status_code=400, detail=f"Revisione rev{indice} già presente")

    stato = resolve_state(payload.stato)
    revisione = models.Revisione(
        codice_id=codice_obj.id,
        indice=indice,
        stato=stato,
        cad_file=payload.cad_file,
    )
    db.add(revisione)
    db.commit()
    db.refresh(revisione)
    _clone_certificazione_from_previous(db, codice_obj.id, revisione)

    log_activity(account_ctx, "revisione_creata", riferimento=f"{payload.codice}:rev{revisione.indice}")
    color = state_color_map().get(revisione.stato.lower(), "#777777")
    return RevisioneResponse(
        indice=revisione.indice,
        stato=revisione.stato,
        color=color,
        cad_file=revisione.cad_file,
        is_released=revisione.is_released,
        released_at=revisione.released_at.isoformat() if revisione.released_at else None,
        files=_files_payload(revisione),
    )


@router.get("/{codice}", response_model=List[RevisioneResponse])
def elenco_revisioni(codice: str, db: Session = Depends(database.get_db)):
    codice_obj = db.query(models.Codice).filter_by(codice=codice).first()
    if not codice_obj:
        raise HTTPException(status_code=404, detail="Codice non trovato")

    color_map = state_color_map()
    return [
        RevisioneResponse(
            indice=rev.indice,
            stato=rev.stato,
            color=color_map.get(rev.stato.lower(), "#777777"),
            cad_file=rev.cad_file,
            is_released=rev.is_released,
            released_at=rev.released_at.isoformat() if rev.released_at else None,
            files=_files_payload(rev),
        )
        for rev in codice_obj.revisioni
    ]


def _get_revision_or_404(db: Session, codice: str, indice: int) -> models.Revisione:
    revisione = (
        db.query(models.Revisione)
        .join(models.Codice)
        .filter(models.Codice.codice == codice, models.Revisione.indice == indice)
        .first()
    )
    if not revisione:
        raise HTTPException(status_code=404, detail="Revisione non trovata")
    return revisione


def _files_payload(revisione: models.Revisione) -> List[RevisioneFilePayload]:
    return [
        RevisioneFilePayload(
            filename=rf.filename,
            mimetype=rf.mimetype,
            uploaded_at=rf.uploaded_at.isoformat() if rf.uploaded_at else None,
        )
        for rf in revisione.files
    ]


def _clone_certificazione_from_previous(db: Session, codice_id: int, nuova_revisione: models.Revisione):
    precedente = (
        db.query(models.Revisione)
        .filter(models.Revisione.codice_id == codice_id, models.Revisione.indice < nuova_revisione.indice)
        .order_by(models.Revisione.indice.desc())
        .first()
    )
    if not precedente:
        return
    if precedente.certificazione:
        for campo in precedente.certificazione:
            clone = models.CertificazioneCampo(
                revisione_id=nuova_revisione.id,
                nome=campo.nome,
                valore=campo.valore,
                ordine=campo.ordine,
            )
            db.add(clone)
    if precedente.cad_file and not nuova_revisione.cad_file:
        nuova_revisione.cad_file = precedente.cad_file
        db.add(nuova_revisione)
    if precedente.files:
        for file_entry in precedente.files:
            src = Path(file_entry.filepath)
            dest_dir = REV_FILES_DIR / str(nuova_revisione.id)
            dest_dir.mkdir(parents=True, exist_ok=True)
            if src.exists():
                new_name = f"{uuid.uuid4().hex}_{Path(file_entry.filename).name}"
                dest_path = dest_dir / new_name
                shutil.copy2(src, dest_path)
                cloned_path = dest_path
                cloned_name = file_entry.filename
            else:
                cloned_path = Path(file_entry.filepath)
                cloned_name = file_entry.filename
            new_file = models.RevisioneFile(
                revisione_id=nuova_revisione.id,
                filename=cloned_name,
                filepath=str(cloned_path),
                mimetype=file_entry.mimetype,
            )
            db.add(new_file)
    db.commit()
    db.refresh(nuova_revisione)


@router.post("/{codice}/{indice}/rilascio", response_model=RevisioneResponse)
def rilascia_revisione(
    codice: str,
    indice: int,
    db: Session = Depends(database.get_db),
    account_ctx: dict = Depends(require_account_context),
):
    revisione = _get_revision_or_404(db, codice, indice)
    if revisione.is_released:
        raise HTTPException(status_code=400, detail="Revisione già rilasciata")

    revisione.is_released = True
    revisione.released_at = func.now()
    db.add(revisione)
    db.commit()
    db.refresh(revisione)

    log_activity(account_ctx, "revisione_rilasciata", riferimento=f"{codice}:rev{indice}")
    color = state_color_map().get(revisione.stato.lower(), "#777777")
    return RevisioneResponse(
        indice=revisione.indice,
        stato=revisione.stato,
        color=color,
        cad_file=revisione.cad_file,
        is_released=revisione.is_released,
        released_at=revisione.released_at.isoformat() if revisione.released_at else None,
        files=_files_payload(revisione),
    )


@router.get("/{codice}/{indice}/certificazione", response_model=List[CertCampo])
def get_certificazione(codice: str, indice: int, db: Session = Depends(database.get_db)):
    revisione = _get_revision_or_404(db, codice, indice)
    fields = load_form_fields()
    existing = {campo.nome.lower(): campo for campo in revisione.certificazione}
    used = set()
    output: List[CertCampo] = []

    for pos, field in enumerate(fields):
        key = field["name"].lower()
        entry = existing.get(key)
        output.append(
            CertCampo(
                nome=field["name"],
                label=field["label"],
                valore=entry.valore if entry else "",
                ordine=field.get("order", pos),
            )
        )
        used.add(key)

    for campo in revisione.certificazione:
        key = campo.nome.lower()
        if key in used:
            continue
        output.append(
            CertCampo(
                nome=campo.nome,
                label=campo.nome.replace("_", " ").title(),
                valore=campo.valore,
                ordine=campo.ordine,
            )
        )

    return output


@router.post("/{codice}/{indice}/certificazione", response_model=List[CertCampo])
def salva_certificazione(
    codice: str,
    indice: int,
    payload: CertPayload,
    db: Session = Depends(database.get_db),
    account_ctx: dict = Depends(require_account_context),
):
    revisione = _get_revision_or_404(db, codice, indice)
    for campo in list(revisione.certificazione):
        db.delete(campo)
    db.flush()

    nuova_lista = []
    for pos, campo in enumerate(payload.campi):
        nome = (campo.nome or "").strip()
        if not nome:
            continue
        entry = models.CertificazioneCampo(
            revisione_id=revisione.id,
            nome=nome,
            valore=(campo.valore or "").strip(),
            ordine=campo.ordine if campo.ordine is not None else pos,
        )
        db.add(entry)
        nuova_lista.append(entry)

    db.commit()
    db.refresh(revisione)

    log_activity(account_ctx, "certificazione_salvata", riferimento=f"{codice}:rev{indice}")
    return get_certificazione(codice, indice, db)


@router.post("/{codice}/{indice}/stato", response_model=RevisioneResponse)
def cambia_stato_revisione(
    codice: str,
    indice: int,
    payload: ChangeStatePayload,
    db: Session = Depends(database.get_db),
    account_ctx: dict = Depends(require_account_context),
):
    revisione = _get_revision_or_404(db, codice, indice)
    if revisione.is_released:
        raise HTTPException(status_code=400, detail="Impossibile cambiare stato a una revisione rilasciata")

    nuovo_stato = resolve_state(payload.stato)
    order_map = state_order_map()
    current_idx = order_map.get(revisione.stato.lower())
    new_idx = order_map.get(nuovo_stato.lower())

    if new_idx is None:
        raise HTTPException(status_code=400, detail="Stato non valido")

    if current_idx is not None and new_idx < current_idx:
        raise HTTPException(status_code=400, detail="Non è possibile retrocedere di stato")

    revisione.stato = nuovo_stato
    db.add(revisione)
    db.commit()
    db.refresh(revisione)

    log_activity(
        account_ctx,
        "revisione_cambia_stato",
        riferimento=f"{codice}:rev{indice}",
        dettagli=f"{revisione.stato}",
    )
    color = state_color_map().get(revisione.stato.lower(), "#777777")
    return RevisioneResponse(
        indice=revisione.indice,
        stato=revisione.stato,
        color=color,
        cad_file=revisione.cad_file,
        is_released=revisione.is_released,
        released_at=revisione.released_at.isoformat() if revisione.released_at else None,
        files=_files_payload(revisione),
    )


@router.get("/{codice}/{indice}/files", response_model=List[RevisioneFilePayload])
def lista_file_revisione(codice: str, indice: int, db: Session = Depends(database.get_db)):
    revisione = _get_revision_or_404(db, codice, indice)
    return _files_payload(revisione)


@router.post("/{codice}/{indice}/files", response_model=List[RevisioneFilePayload])
async def carica_file_revisione(
    codice: str,
    indice: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(database.get_db),
    account_ctx: dict = Depends(require_account_context),
):
    revisione = _get_revision_or_404(db, codice, indice)
    if revisione.is_released:
        raise HTTPException(status_code=400, detail="Revisione rilasciata: impossibile caricare file")
    if not files:
        raise HTTPException(status_code=400, detail="Nessun file ricevuto")

    saved_records = []
    for upload in files:
        dest_dir = REV_FILES_DIR / str(revisione.id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{upload.filename}"
        dest_path = dest_dir / unique_name
        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)
        record = models.RevisioneFile(
            revisione_id=revisione.id,
            filename=upload.filename,
            filepath=str(dest_path),
            mimetype=upload.content_type or "",
        )
        db.add(record)
        saved_records.append(record)

    db.commit()
    db.refresh(revisione)
    log_activity(
        account_ctx,
        "revisione_carica_file",
        riferimento=f"{codice}:rev{indice}",
        dettagli=f"{len(saved_records)} file",
    )
    return _files_payload(revisione)
