import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox, QToolButton, QDialog
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from ui_mainwindow import MainWindowUI
from api_client import APIClient
from bom_loader import BOMLoaderWindow
from account_dialog import AccountSelectionDialog
from account_store import (
    load_account_context,
    save_account_context,
    clear_account_context,
    load_font_scale,
    save_font_scale,
    load_account_password,
    save_account_password,
)
from settings_dialog import SettingsDialog

class PLMClient(MainWindowUI):
    def __init__(self):
        super().__init__()
        self.api = APIClient()
        self._codici_cache = []
        self._codici_by_code = {}
        self._bom_cache = {}
        self._codes_with_bom = set()
        self._bom_window = None
        self._states = []
        self._account_info = None
        self._settings_dialog = None
        self._font_scale = load_font_scale()
        app = QApplication.instance()
        base_font = app.font() if app else None
        self._base_font_point_size = (base_font.pointSizeF() if base_font and base_font.pointSizeF() > 0 else 10.0)
        self._apply_font_scale(self._font_scale)
        self._ensure_account_session()
        self._load_states()

        for filtro in getattr(self, "filter_inputs", []):
            if filtro is None:
                continue
            filtro.textChanged.connect(self._apply_filters)

        self.btn_new.clicked.connect(self.nuovo_codice)
        self.btn_load_bom.clicked.connect(self.apri_carica_distinta)
        self.btn_settings.clicked.connect(self._open_settings)
        self.carica_lista()  # carica all'avvio
        

    def carica_lista(self):
        try:
            codici = self.api.lista_codici()
            self._codici_cache = codici
            self._codici_by_code = {c.get("codice"): c for c in codici}
            self._preload_bom_presence()
            self._apply_filters()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore di connessione:\n{e}")

    def _ensure_account_session(self):
        saved = load_account_context()
        saved_password = load_account_password()
        if saved and saved_password:
            if self._attempt_login(saved, saved_password, persist=False, show_errors=False):
                return
            save_account_password("")
        self._prompt_account_selection()

    def _prompt_account_selection(self):
        try:
            hierarchy = self.api.lista_account_hierarchy()
        except Exception as exc:
            QMessageBox.critical(self, "Connessione account", f"Impossibile scaricare la lista account:\n{exc}")
            sys.exit(1)

        if not hierarchy:
            QMessageBox.critical(self, "Account mancanti", "Nessun account configurato sul server.")
            sys.exit(1)

        while True:
            dialog = AccountSelectionDialog(hierarchy, self, api_client=self.api)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                QMessageBox.warning(self, "Account richiesto", "Per continuare è necessario selezionare un account.")
                sys.exit(0)
            selection = dialog.selected_account()
            password = dialog.selected_password()
            if not password:
                QMessageBox.warning(self, "Password mancante", "Inserisci la password per continuare.")
                continue
            if self._attempt_login(selection, password, persist=True, show_errors=True):
                break

    def _attempt_login(self, selection, password: str, *, persist: bool, show_errors: bool) -> bool:
        try:
            verified = self.api.login_account(
                selection["stabilimento"],
                selection["gruppo"],
                selection["account"],
                password,
            )
        except Exception as exc:
            if show_errors:
                QMessageBox.warning(self, "Login account", f"Impossibile autenticare l'account selezionato:\n{exc}")
            return False
        self.api.set_account_context(verified)
        self._account_info = verified
        if persist:
            save_account_context(verified)
            save_account_password(password)
        return True

    def _apply_font_scale(self, scale: float):
        app = QApplication.instance()
        if not app:
            self._font_scale = scale
            return
        base_size = getattr(self, "_base_font_point_size", 10.0)
        new_font = QFont(app.font())
        new_font.setPointSizeF(max(8.0, base_size * scale))
        app.setFont(new_font)
        self._font_scale = scale

    def _open_settings(self):
        if self._settings_dialog and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return
        dialog = SettingsDialog(self._font_scale, self)
        dialog.fontScaleChanged.connect(self._handle_font_scale_changed)
        dialog.logoutRequested.connect(self._handle_logout_request)
        self._settings_dialog = dialog
        dialog.exec()
        self._settings_dialog = None

    def _handle_font_scale_changed(self, scale: float):
        if abs(scale - self._font_scale) < 0.01:
            return
        self._apply_font_scale(scale)
        save_font_scale(scale)

    def _handle_logout_request(self):
        confirm = QMessageBox.question(
            self,
            "Logout",
            "Vuoi disconnettere l'account corrente? Dovrai effettuare nuovamente il login.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._perform_logout()
        if self._settings_dialog:
            self._settings_dialog.reject()

    def _perform_logout(self):
        clear_account_context()
        self.api.set_account_context(None)
        self._account_info = None
        if self._bom_window:
            self._bom_window.close()
            self._bom_window = None
        self._codici_cache.clear()
        self._codici_by_code.clear()
        self._bom_cache.clear()
        self._codes_with_bom.clear()
        self._clear_data_rows()
        python = sys.executable
        script = Path(__file__).resolve()

        def _restart():
            os.execv(python, [python, str(script)])

        QTimer.singleShot(0, _restart)

    def nuovo_codice(self):
        from PySide6.QtWidgets import QInputDialog, QMessageBox

        tipo, ok1 = QInputDialog.getText(self, "Nuovo codice", "Tipo (es. 00, 03, 05):")
        if not ok1 or not tipo.strip():
            return

        descrizione, ok2 = QInputDialog.getText(self, "Nuovo codice", "Descrizione:")
        if not ok2:
            return

        quantita, ok3 = QInputDialog.getDouble(self, "Nuovo codice", "Quantità:", 0, 0)
        if not ok3:
            return

        ubicazione, ok4 = QInputDialog.getText(self, "Nuovo codice", "Ubicazione:")
        if not ok4:
            return

        stato_names = [s.get("name", "") for s in self._states if s.get("name")] or ["concept"]
        stato, ok5 = QInputDialog.getItem(
            self,
            "Stato di rilascio",
            "Seleziona lo stato iniziale:",
            stato_names,
            0,
            False,
        )
        if not ok5:
            return

        try:
            nuovo = self.api.crea_codice(
                tipo.strip(),
                descrizione,
                quantita,
                ubicazione,
                stato=stato,
                rilascia_subito=True,
            )
            QMessageBox.information(self, "Successo", f"Codice generato: {nuovo['codice']}")
            self.carica_lista()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile creare codice:\n{e}")

    
    def apri_carica_distinta(self):
        if self._bom_window is None:
            self._bom_window = BOMLoaderWindow(self.api, self)
        self._bom_window.show()
        self._bom_window.raise_()
        self._bom_window.activateWindow()


    def _apply_filters(self, *_):
        filtri = []
        for col, filtro in enumerate(getattr(self, "filter_inputs", [])):
            if not filtro:
                continue
            testo = filtro.text().strip().lower()
            if testo:
                filtri.append((col, testo))

        filtrati = []
        for codice in self._codici_cache:
            valori = {
                1: str(codice.get("codice", "")),
                2: str(codice.get("descrizione", "")),
                3: str(codice.get("quantita", "")),
                4: str(codice.get("ubicazione", "")),
            }

            if all(testo in valori[col].lower() for col, testo in filtri):
                filtrati.append(codice)

        self._mostra_codici(filtrati)


    def _mostra_codici(self, codici):
        self._clear_data_rows()

        for codice in codici:
            row = self.table.rowCount()
            self.table.insertRow(row)

            code = str(codice.get("codice", ""))
            descrizione = str(codice.get("descrizione", ""))
            quantita = str(codice.get("quantita", ""))
            ubicazione = str(codice.get("ubicazione", ""))

            self._set_row_content(row, code, descrizione, quantita, ubicazione, level=0, parent=None)
            self._setup_indicator(row, code)

    def _clear_data_rows(self):
        while self.table.rowCount() > 1:
            self.table.removeRow(1)

    def _set_row_content(self, row, codice, descrizione, quantita, ubicazione, *, level, parent):
        indent = "    " * level
        item_codice = self._item(f"{indent}{codice}")
        item_codice.setData(Qt.ItemDataRole.UserRole, {
            "code": codice,
            "level": level,
            "parent": parent,
        })
        self.table.setItem(row, 1, item_codice)
        self.table.setItem(row, 2, self._item(descrizione))
        self.table.setItem(row, 3, self._item(quantita))
        self.table.setItem(row, 4, self._item(ubicazione))

    def _setup_indicator(self, row, codice):
        existing = self.table.cellWidget(row, 0)
        if existing:
            self.table.removeCellWidget(row, 0)
            existing.deleteLater()

        has_children = codice in self._codes_with_bom and bool(self._bom_cache.get(codice))
        if has_children:
            button = self._create_expand_button(codice)
            self.table.setCellWidget(row, 0, button)
        else:
            self.table.setItem(row, 0, self._item(""))

    def _create_expand_button(self, codice):
        button = QToolButton(self.table)
        button.setCheckable(True)
        button.setArrowType(Qt.ArrowType.RightArrow)
        button.setAutoRaise(True)
        button.setProperty("code", codice)
        button.clicked.connect(lambda checked, b=button: self._handle_expand_clicked(b, checked))
        return button

    def _handle_expand_clicked(self, button, checked):
        row = self._row_for_button(button)
        if row is None:
            return

        codice = button.property("code")
        if not codice:
            return

        if checked:
            if not self._expand_row(row, codice):
                button.setChecked(False)
        else:
            self._remove_subtree(row)

    def _row_for_button(self, button):
        for row in range(1, self.table.rowCount()):
            if self.table.cellWidget(row, 0) is button:
                return row
        return None

    def _expand_row(self, row, codice):
        bom = self._get_bom_for_code(codice)
        if not bom:
            QMessageBox.information(self, "Distinta", f"Nessuna distinta disponibile per {codice}.")
            return False

        row_data = self._row_data(row)
        level = row_data.get("level", 0) + 1

        insert_at = row + 1
        for componente in bom:
            codice_figlio = componente.get("figlio") or ""
            descrizione, ubicazione = self._child_display_data(codice_figlio, componente)
            quantita = str(componente.get("quantita", ""))

            self.table.insertRow(insert_at)
            self._set_row_content(
                insert_at,
                codice_figlio,
                descrizione,
                quantita,
                ubicazione,
                level=level,
                parent=codice,
            )
            self._ensure_bom_cached(codice_figlio)
            self._setup_indicator(insert_at, codice_figlio)
            insert_at += 1

        button = self.table.cellWidget(row, 0)
        if button:
            button.setArrowType(Qt.ArrowType.DownArrow)
        return True

    def _get_bom_for_code(self, codice):
        self._ensure_bom_cached(codice)
        return self._bom_cache.get(codice) or []

    def _row_data(self, row):
        if row <= 0 or row >= self.table.rowCount():
            return {}
        item = self.table.item(row, 1)
        if not item:
            return {}
        data = item.data(Qt.ItemDataRole.UserRole)
        return data or {}

    def _remove_subtree(self, row):
        data = self._row_data(row)
        level = data.get("level", 0)
        current = row + 1
        while current < self.table.rowCount():
            child_data = self._row_data(current)
            if not child_data or child_data.get("level", 0) <= level:
                break
            widget = self.table.cellWidget(current, 0)
            if widget:
                widget.deleteLater()
            self.table.removeRow(current)

        button = self.table.cellWidget(row, 0)
        if button:
            button.setArrowType(Qt.ArrowType.RightArrow)
            button.setChecked(False)

    def _ensure_bom_cached(self, codice, *, force=False):
        if not codice:
            return

        if not force and codice in self._bom_cache and self._bom_cache[codice] is not None:
            return

        try:
            distinta = self.api.distinta(codice)
        except Exception:
            self._bom_cache[codice] = []
            return

        self._bom_cache[codice] = distinta
        if distinta:
            self._codes_with_bom.add(codice)
        else:
            self._codes_with_bom.discard(codice)

    def _child_display_data(self, codice, componente):
        descrizione = componente.get("descrizione")
        if not descrizione and codice in self._codici_by_code:
            descrizione = self._codici_by_code[codice].get("descrizione", "")

        ubicazione = ""
        if codice in self._codici_by_code:
            ubicazione = self._codici_by_code[codice].get("ubicazione", "")

        return str(descrizione or ""), str(ubicazione or "")

    def _preload_bom_presence(self):
        self._bom_cache = {}
        self._codes_with_bom = set()
        for codice in self._codici_cache:
            code_value = codice.get("codice")
            if not code_value:
                continue
            try:
                distinta = self.api.distinta(code_value)
            except Exception:
                self._bom_cache[code_value] = []
                continue
            self._bom_cache[code_value] = distinta
            if distinta:
                self._codes_with_bom.add(code_value)

    def on_bom_row_sent(self, codice_padre):
        self._ensure_bom_cached(codice_padre, force=True)
        self._apply_filters()

    def _load_states(self):
        try:
            self._states = self.api.lista_stati()
        except Exception:
            self._states = [{"name": "concept"}]


    def _item(self, text):
        """Crea una cella di tabella non modificabile"""
        from PySide6.QtWidgets import QTableWidgetItem
        from PySide6.QtCore import Qt

        item = QTableWidgetItem(str(text))
        # Rende la cella sola lettura
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PLMClient()
    window.show()
    sys.exit(app.exec())
