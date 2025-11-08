import httpx
import mimetypes
from pathlib import Path


class APIClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url

    def lista_codici(self, include_unreleased=True):
        """Ottiene tutti i codici visibili al client tecnico"""
        params = {"include_unreleased": str(include_unreleased).lower()} if include_unreleased else {}
        r = httpx.get(f"{self.base_url}/codici/", params=params or None)
        r.raise_for_status()
        return r.json()

    def cerca_codice(self, codice, include_unreleased=True):
        """Cerca un singolo codice"""
        params = {"include_unreleased": str(include_unreleased).lower()} if include_unreleased else None
        r = httpx.get(f"{self.base_url}/codici/{codice}", params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def dettaglio_codice(self, codice, include_unreleased=True):
        """Restituisce codice, descrizione, revisioni e file"""
        params = {"include_unreleased": str(include_unreleased).lower()} if include_unreleased else None
        r = httpx.get(f"{self.base_url}/codici/{codice}/dettaglio", params=params)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def crea_codice(self, codice, descrizione, quantita, ubicazione, stato=None):
        """Crea un nuovo codice nel database PLM"""
        payload = {
            "codice": codice,
            "descrizione": descrizione,
            "quantita": quantita,
            "ubicazione": ubicazione,
            "rilascia_subito": False,
        }
        if stato:
            payload["stato"] = stato
        r = httpx.post(f"{self.base_url}/codici/", json=payload)
        r.raise_for_status()
        return r.json()

    def lista_stati(self):
        """Recupera gli stati configurati lato server"""
        r = httpx.get(f"{self.base_url}/stati/")
        r.raise_for_status()
        return r.json()

    def lista_campi_form(self):
        """Recupera la lista di campi del form certificazione"""
        r = httpx.get(f"{self.base_url}/form/campi")
        r.raise_for_status()
        return r.json()

    def rilascia_revisione(self, codice, indice):
        r = httpx.post(f"{self.base_url}/revisioni/{codice}/{indice}/rilascio")
        r.raise_for_status()
        return r.json()

    def crea_revisione(self, codice, stato=None, cad_file=None):
        payload = {"codice": codice}
        if stato:
            payload["stato"] = stato
        if cad_file:
            payload["cad_file"] = cad_file
        r = httpx.post(f"{self.base_url}/revisioni/", json=payload)
        r.raise_for_status()
        return r.json()

    def cambia_stato_revisione(self, codice, indice, nuovo_stato):
        payload = {"stato": nuovo_stato}
        r = httpx.post(f"{self.base_url}/revisioni/{codice}/{indice}/stato", json=payload)
        r.raise_for_status()
        return r.json()

    def get_certificazione(self, codice, indice):
        r = httpx.get(f"{self.base_url}/revisioni/{codice}/{indice}/certificazione")
        r.raise_for_status()
        return r.json()

    def salva_certificazione(self, codice, indice, campi):
        payload = {"campi": campi}
        r = httpx.post(f"{self.base_url}/revisioni/{codice}/{indice}/certificazione", json=payload)
        r.raise_for_status()
        return r.json()

    def lista_file_revisione(self, codice, indice):
        r = httpx.get(f"{self.base_url}/revisioni/{codice}/{indice}/files")
        r.raise_for_status()
        return r.json()

    def carica_file_revisione(self, codice, indice, filepath):
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(path)
        mime, _ = mimetypes.guess_type(str(path))
        with path.open("rb") as buffer:
            files = [("files", (path.name, buffer.read(), mime or "application/octet-stream"))]
            r = httpx.post(f"{self.base_url}/revisioni/{codice}/{indice}/files", files=files)
        r.raise_for_status()
        return r.json()
