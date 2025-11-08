import httpx
from typing import Dict, Optional


class APIClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self._account_context: Optional[Dict[str, str]] = None

    def set_account_context(self, context: Optional[Dict[str, str]]):
        if context:
            header_value = f"{context['stabilimento']}|{context['gruppo']}|{context['account']}"
            context = {**context, "header": header_value}
        self._account_context = context

    def _auth_headers(self) -> Dict[str, str]:
        if not self._account_context or not self._account_context.get("header"):
            raise RuntimeError("Nessun account selezionato.")
        return {"X-PLM-Account": self._account_context["header"]}

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
        r = httpx.post(f"{self.base_url}/codici/", json=payload, headers=self._auth_headers())
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
        r = httpx.post(f"{self.base_url}/distinte/", params=params, headers=self._auth_headers())
        r.raise_for_status()
        return r.json()

    def distinta(self, codice):
        """Recupera la distinta base di un codice"""
        r = httpx.get(f"{self.base_url}/distinte/{codice}")
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json()

    def lista_account_hierarchy(self):
        r = httpx.get(f"{self.base_url}/auth/accounts")
        r.raise_for_status()
        return r.json()

    def login_account(self, stabilimento: str, gruppo: str, account: str, password: str):
        payload = {
            "stabilimento": stabilimento,
            "gruppo": gruppo,
            "account": account,
            "password": password,
        }
        r = httpx.post(f"{self.base_url}/auth/login", json=payload)
        r.raise_for_status()
        return r.json()

    def crea_account_login(self, account: str, password: str):
        payload = {"account": account, "password": password}
        r = httpx.post(f"{self.base_url}/auth/accounts", json=payload)
        r.raise_for_status()
        return r.json()

    def password_policy(self):
        r = httpx.get(f"{self.base_url}/auth/policy")
        r.raise_for_status()
        return r.json()
