from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core import models, database
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/codici", tags=["Codici"])

# Schema Pydantic per input/output
class CodiceBase(BaseModel):
    codice: str
    descrizione: str
    quantita: float
    ubicazione: str

    model_config = {
        "from_attributes": True
    }


@router.post("/", response_model=CodiceBase)
def crea_codice(codice: CodiceBase, db: Session = Depends(database.get_db)):
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

    return db_codice


@router.get("/", response_model=List[CodiceBase])
def lista_codici(db: Session = Depends(database.get_db)):
    return db.query(models.Codice).all()

@router.get("/{codice}", response_model=CodiceBase)
def leggi_codice(codice: str, db: Session = Depends(database.get_db)):
    db_codice = db.query(models.Codice).filter(models.Codice.codice == codice).first()
    if not db_codice:
        raise HTTPException(status_code=404, detail="Codice non trovato")
    return db_codice
