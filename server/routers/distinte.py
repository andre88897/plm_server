from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core import models, database

router = APIRouter(prefix="/distinte", tags=["distinte"])

@router.post("/")
def aggiungi_componente(padre: str, figlio: str, quantita: float = 1.0, db: Session = Depends(database.get_db)):
    codice_padre = db.query(models.Codice).filter_by(codice=padre).first()
    codice_figlio = db.query(models.Codice).filter_by(codice=figlio).first()

    if not codice_padre or not codice_figlio:
        raise HTTPException(status_code=404, detail="Codice padre o figlio non trovato")

    distinta = models.Distinta(padre_id=codice_padre.id, figlio_id=codice_figlio.id, quantita=quantita)
    db.add(distinta)
    db.commit()
    return {"msg": f"Aggiunto {figlio} a {padre} (qta={quantita})"}

@router.get("/{codice}")
def get_distinta(codice: str, db: Session = Depends(database.get_db)):
    codice_padre = db.query(models.Codice).filter_by(codice=codice).first()
    if not codice_padre:
        raise HTTPException(status_code=404, detail="Codice non trovato")

    distinte = db.query(models.Distinta).filter_by(padre_id=codice_padre.id).all()
    return [
        {
            "figlio": d.figlio.codice,
            "descrizione": d.figlio.descrizione,
            "quantita": d.quantita
        }
        for d in distinte
    ]
