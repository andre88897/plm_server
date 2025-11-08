import httpx


class APIClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url

    def lista_codici(self):
        """Ottiene tutti i codici rilasciati dal server"""
        r = httpx.get(f"{self.base_url}/codici/")
        r.raise_for_status()
        return r.json()

    def cerca_codice(self, codice):
        """Cerca un singolo codice rilasciato"""
        r = httpx.get(f"{self.base_url}/codici/{codice}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def crea_codice(self, codice, descrizione, quantita, ubicazione, stato=None, rilascia_subito=False):
        """Crea un nuovo codice nel database PLM"""
        payload = {
            "codice": codice,
            "descrizione": descrizione,
            "quantita": quantita,
            "ubicazione": ubicazione,
            "rilascia_subito": bool(rilascia_subito),
        }
        if stato:
            payload["stato"] = stato
        r = httpx.post(f"{self.base_url}/codici/", json=payload)
        r.raise_for_status()
        return r.json()

    def lista_stati(self):
        r = httpx.get(f"{self.base_url}/stati/")
        r.raise_for_status()
        return r.json()

    def aggiungi_componente(self, padre, figlio, quantita):
        """Aggiunge un componente a una distinta base"""
        params = {
            "padre": padre,
            "figlio": figlio,
            "quantita": quantita,
        }
        r = httpx.post(f"{self.base_url}/distinte/", params=params)
        r.raise_for_status()
        return r.json()

    def distinta(self, codice):
        """Recupera la distinta base di un codice"""
        r = httpx.get(f"{self.base_url}/distinte/{codice}")
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json()
