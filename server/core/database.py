# server/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Percorso del database locale
SQLALCHEMY_DATABASE_URL = "sqlite:///./plm.db"

# Connessione con SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Crea la base per i modelli
Base = declarative_base()

# Sessione DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



SQLALCHEMY_DATABASE_URL = "sqlite:///./plm.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ Questa funzione fornisce la sessione DB a FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()