from fastapi import APIRouter
from core.form_manager import load_form_fields

router = APIRouter(prefix="/form", tags=["Form"])


@router.get("/campi")
def lista_campi_form():
    return load_form_fields()
