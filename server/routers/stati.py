from fastapi import APIRouter
from core.state_manager import load_states

router = APIRouter(prefix="/stati", tags=["Stati"])


@router.get("/")
def elenco_stati():
    return load_states()
