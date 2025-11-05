from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship 
from .database import Base


#Informazioni base sui codici
class Codice(Base):
    __tablename__ = "codici"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String, unique=True, index=True)
    descrizione = Column(String)
    quantita = Column(Float)
    ubicazione = Column(String)

    #Aggiungiamo il link ai file CAD associati
    files = relationship("FileModel", back_populates="codice", cascade="all, delete-orphan")

#Modello per i file CAD associati ai codici
class FileModel(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    codice_id = Column(Integer, ForeignKey("codici.id"))
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    filetype = Column(String, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    codice = relationship("Codice", back_populates="files")


#Modello per le distinte base (BOM)
class Distinta(Base):
    __tablename__ = "distinte"

    id = Column(Integer, primary_key=True, index=True)
    padre_id = Column(Integer, ForeignKey("codici.id"), nullable=False)
    figlio_id = Column(Integer, ForeignKey("codici.id"), nullable=False)
    quantita = Column(Float, default=1.0)

    padre = relationship("Codice", foreign_keys=[padre_id], backref="componenti")
    figlio = relationship("Codice", foreign_keys=[figlio_id])
