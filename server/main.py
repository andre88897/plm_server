from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core import models, database
from routers import codici, files, distinte


# ✅ Crea tabelle nel database se non esistono
models.Base.metadata.create_all(bind=database.engine)

# ✅ Inizializza FastAPI
app = FastAPI(
    title="PLM Server",
    description="Server PLM per gestione codici, magazzino e file tecnici",
    version="1.0.0",
)

# ✅ Abilita CORS (per permettere a client su altre macchine di collegarsi)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # puoi limitarlo in futuro
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Registra i router
app.include_router(codici.router)
app.include_router(files.router)
app.include_router(distinte.router)

# ✅ Endpoint di test
@app.get("/")
def root():
    return {"status": "ok", "message": "PLM Server attivo"}

# ✅ Avvio del server
# (da terminale: uvicorn main:app --reload)
