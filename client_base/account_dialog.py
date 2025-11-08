from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QFormLayout,
    QPushButton,
    QInputDialog,
    QLineEdit,
)
from PySide6.QtCore import Qt


class AccountSelectionDialog(QDialog):
    def __init__(self, hierarchy: List[Dict[str, object]], parent=None, api_client=None):
        super().__init__(parent)
        self.setWindowTitle("Seleziona account")
        self.setModal(True)
        self.resize(480, 260)

        self._api = api_client
        self._policy = self._fetch_policy()
        self._hierarchy_map = self._build_map(hierarchy or [])

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        label = QLabel("Seleziona stabilimento, gruppo di lavoro e account da utilizzare su questo dispositivo.")
        label.setWordWrap(True)
        layout.addWidget(label)

        form = QFormLayout()
        form.setSpacing(8)
        layout.addLayout(form)

        self.stabilimento_combo = QComboBox()
        self.gruppo_combo = QComboBox()
        self.account_combo = QComboBox()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Stabilimento", self.stabilimento_combo)
        form.addRow("Gruppo", self.gruppo_combo)
        form.addRow("Account", self.account_combo)
        form.addRow("Password", self.password_input)

        policy_text = self._policy_summary()
        self.policy_label = QLabel(policy_text) if policy_text else None
        if self.policy_label:
            self.policy_label.setWordWrap(True)
            self.policy_label.setStyleSheet("color: #4b5563; font-size: 12px;")
            layout.addWidget(self.policy_label)

        self.stabilimento_combo.currentTextChanged.connect(self._populate_groups)
        self.gruppo_combo.currentTextChanged.connect(self._populate_accounts)

        self.btn_create_account = QPushButton("Crea nuovo account")
        self.btn_create_account.clicked.connect(self._handle_create_account)
        self.btn_create_account.setEnabled(self._api is not None)
        layout.addWidget(self.btn_create_account, alignment=Qt.AlignmentFlag.AlignLeft)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._handle_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._populate_stabilimenti()

    def _build_map(self, hierarchy: List[Dict[str, object]]):
        result: Dict[str, Dict[str, List[str]]] = {}
        for stabilimento in hierarchy:
            name = str(stabilimento.get("stabilimento") or "").strip()
            if not name:
                continue
            gruppi_map: Dict[str, List[str]] = {}
            for gruppo in stabilimento.get("gruppi") or []:
                group_name = str(gruppo.get("nome") or "").strip()
                if not group_name:
                    continue
                accounts = [str(acc).strip() for acc in (gruppo.get("accounts") or []) if str(acc).strip()]
                gruppi_map[group_name] = accounts
            if gruppi_map:
                result[name] = gruppi_map
        return result

    def _populate_stabilimenti(self):
        self.stabilimento_combo.blockSignals(True)
        self.stabilimento_combo.clear()
        for name in sorted(self._hierarchy_map.keys()):
            self.stabilimento_combo.addItem(name)
        self.stabilimento_combo.blockSignals(False)
        self._populate_groups(self.stabilimento_combo.currentText())

    def _populate_groups(self, stabilimento: str):
        self.gruppo_combo.blockSignals(True)
        self.gruppo_combo.clear()
        groups = self._hierarchy_map.get(stabilimento, {})
        for name in sorted(groups.keys()):
            self.gruppo_combo.addItem(name)
        self.gruppo_combo.blockSignals(False)
        self._populate_accounts(self.gruppo_combo.currentText())

    def _populate_accounts(self, gruppo: str):
        stabilimento = self.stabilimento_combo.currentText()
        accounts = self._hierarchy_map.get(stabilimento, {}).get(gruppo, [])
        self.account_combo.clear()
        for account in sorted(accounts):
            self.account_combo.addItem(account)
        self.password_input.clear()

    def _fetch_policy(self) -> Optional[Dict[str, object]]:
        if not self._api:
            return None
        try:
            return self._api.password_policy()
        except Exception:
            return None

    def _policy_summary(self) -> str:
        if not self._policy:
            return ""
        parts = [f"Lunghezza minima {self._policy.get('min_length', 8)}"]
        if self._policy.get("require_digit"):
            parts.append("1 cifra")
        if self._policy.get("require_symbol"):
            parts.append("1 simbolo")
        if self._policy.get("require_upper"):
            parts.append("1 maiuscola")
        return "Requisiti password: " + ", ".join(parts)

    def _handle_create_account(self):
        if not self._api:
            QMessageBox.information(self, "Non disponibile", "Funzione non disponibile senza connessione al server.")
            return
        account_name, ok = QInputDialog.getText(self, "Nuovo account", "Nome account:")
        if not ok or not account_name.strip():
            return
        password = self._prompt_new_password()
        if not password:
            return
        try:
            created = self._api.crea_account_login(account_name.strip(), password)
        except Exception as exc:
            QMessageBox.warning(self, "Creazione account", f"Impossibile creare l'account:\n{exc}")
            return
        QMessageBox.information(
            self,
            "Account creato",
            f"L'account '{created['account']}' è stato creato con stabilimento e gruppo da assegnare.",
        )
        self._reload_hierarchy_from_server(created)

    def _reload_hierarchy_from_server(self, focus: Optional[Dict[str, str]] = None):
        if not self._api:
            return
        try:
            hierarchy = self._api.lista_account_hierarchy()
        except Exception as exc:
            QMessageBox.warning(self, "Aggiornamento account", f"Impossibile aggiornare la lista account:\n{exc}")
            return
        self._hierarchy_map = self._build_map(hierarchy or [])
        self._populate_stabilimenti()
        if focus:
            self._select_account(
                focus.get("stabilimento"),
                focus.get("gruppo"),
                focus.get("account"),
            )

    def _select_account(self, stabilimento: Optional[str], gruppo: Optional[str], account: Optional[str]):
        if stabilimento:
            idx = self.stabilimento_combo.findText(stabilimento)
            if idx >= 0:
                self.stabilimento_combo.setCurrentIndex(idx)
            else:
                return
        self._populate_groups(self.stabilimento_combo.currentText())
        if gruppo:
            idx = self.gruppo_combo.findText(gruppo)
            if idx >= 0:
                self.gruppo_combo.setCurrentIndex(idx)
        self._populate_accounts(self.gruppo_combo.currentText())
        if account:
            idx = self.account_combo.findText(account)
            if idx >= 0:
                self.account_combo.setCurrentIndex(idx)

    def _handle_accept(self):
        if not self.stabilimento_combo.currentText() or not self.gruppo_combo.currentText() or not self.account_combo.currentText():
            QMessageBox.warning(self, "Selezione incompleta", "Compila stabilimento, gruppo e account.")
            return
        if not self.password_input.text():
            QMessageBox.warning(self, "Password mancante", "Inserisci la password dell'account selezionato.")
            return
        self.accept()

    def selected_account(self) -> Dict[str, str]:
        return {
            "stabilimento": self.stabilimento_combo.currentText(),
            "gruppo": self.gruppo_combo.currentText(),
            "account": self.account_combo.currentText(),
        }

    def selected_password(self) -> str:
        return self.password_input.text()

    def _prompt_new_password(self) -> Optional[str]:
        if not self._api:
            return None
        password, ok = QInputDialog.getText(
            self,
            "Password account",
            self._policy_summary() or "Inserisci la password",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not password:
            return None
        confirm, ok2 = QInputDialog.getText(
            self,
            "Conferma password",
            "Ripeti la password",
            QLineEdit.EchoMode.Password,
        )
        if not ok2 or password != confirm:
            QMessageBox.warning(self, "Errore", "Le password non coincidono.")
            return None
        errors = self._local_password_errors(password)
        if errors:
            QMessageBox.warning(self, "Password debole", "\n".join(errors))
            return None
        return password

    def _local_password_errors(self, password: str) -> List[str]:
        if not self._policy:
            return []
        errors = []
        min_length = int(self._policy.get("min_length", 8))
        if len(password) < min_length:
            errors.append(f"Almeno {min_length} caratteri.")
        if self._policy.get("require_digit") and not any(ch.isdigit() for ch in password):
            errors.append("Almeno una cifra.")
        symbols = set("!@#$%^&*()-_=+[]{};:,.<>?/\\|`~\"'")
        if self._policy.get("require_symbol") and not any(ch in symbols for ch in password):
            errors.append("Almeno un simbolo speciale.")
        if self._policy.get("require_upper") and not any(ch.isupper() for ch in password):
            errors.append("Almeno una lettera maiuscola.")
        return errors
