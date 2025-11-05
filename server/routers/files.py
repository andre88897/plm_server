from fastapi import APIRouter, UploadFile, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from core import models, database
import os, shutil

router = APIRouter(prefix="/files", tags=["Files"])

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(
    codice: str = Form(...),
    descrizione: str = Form(""),
    file: UploadFile = None,
    db: Session = Depends(database.get_db)
):
    # verifica codice esistente
    codice_obj = db.query(models.Codice).filter(models.Codice.codice == codice).first()
    if not codice_obj:
        raise HTTPException(status_code=404, detail=f"Codice {codice} non trovato")

    # salva file
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # registra nel DB
    new_file = models.FileModel(
        codice_id=codice_obj.id,
        filename=file.filename,
        filepath=save_path,
        filetype=file.content_type or "",
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    return {
        "codice": codice,
        "file": file.filename,
        "path": save_path,
        "id": new_file.id,
    }

@router.get("/{codice}")
def list_files(codice: str, db: Session = Depends(database.get_db)):
    codice_obj = db.query(models.Codice).filter(models.Codice.codice == codice).first()
    if not codice_obj:
        raise HTTPException(status_code=404, detail="Codice non trovato")

    return [
        {"filename": f.filename, "uploaded_at": f.uploaded_at, "filetype": f.filetype}
        for f in codice_obj.files
    ]
