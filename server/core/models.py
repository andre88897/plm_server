from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func, Boolean
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
    revisioni = relationship(
        "Revisione",
        back_populates="codice",
        cascade="all, delete-orphan",
        order_by="Revisione.indice",
    )

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


class Revisione(Base):
    __tablename__ = "revisioni"

    id = Column(Integer, primary_key=True, index=True)
    codice_id = Column(Integer, ForeignKey("codici.id"), nullable=False)
    indice = Column(Integer, nullable=False, default=0)
    stato = Column(String, nullable=False, default="concept")
    cad_file = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_released = Column(Boolean, default=False, nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)

    codice = relationship("Codice", back_populates="revisioni")
    certificazione = relationship(
        "CertificazioneCampo",
        back_populates="revisione",
        cascade="all, delete-orphan",
        order_by="CertificazioneCampo.ordine",
    )
    files = relationship(
        "RevisioneFile",
        back_populates="revisione",
        cascade="all, delete-orphan",
        order_by="RevisioneFile.uploaded_at",
    )


class CertificazioneCampo(Base):
    __tablename__ = "certificazioni"

    id = Column(Integer, primary_key=True, index=True)
    revisione_id = Column(Integer, ForeignKey("revisioni.id"), nullable=False)
    nome = Column(String, nullable=False)
    valore = Column(String, nullable=True)
    ordine = Column(Integer, nullable=False, default=0)

    revisione = relationship("Revisione", back_populates="certificazione")


class RevisioneFile(Base):
    __tablename__ = "revisioni_file"

    id = Column(Integer, primary_key=True, index=True)
    revisione_id = Column(Integer, ForeignKey("revisioni.id"), nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    mimetype = Column(String, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    revisione = relationship("Revisione", back_populates="files")


#Modello per le distinte base (BOM)
class Distinta(Base):
    __tablename__ = "distinte"

    id = Column(Integer, primary_key=True, index=True)
    padre_id = Column(Integer, ForeignKey("codici.id"), nullable=False)
    figlio_id = Column(Integer, ForeignKey("codici.id"), nullable=False)
    quantita = Column(Float, default=1.0)

    padre = relationship("Codice", foreign_keys=[padre_id], backref="componenti")
    figlio = relationship("Codice", foreign_keys=[figlio_id])


class AttivitaLog(Base):
    __tablename__ = "attivita_log"

    id = Column(Integer, primary_key=True, index=True)
    account = Column(String, nullable=False)
    stabilimento = Column(String, nullable=False)
    gruppo = Column(String, nullable=False)
    azione = Column(String, nullable=False)
    riferimento = Column(String, nullable=True)
    dettagli = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AccountCredential(Base):
    __tablename__ = "account_credentials"

    id = Column(Integer, primary_key=True, index=True)
    account = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
