import sys
from PySide6.QtWidgets import QApplication, QMessageBox, QToolButton
from PySide6.QtCore import Qt
from ui_mainwindow import MainWindowUI
from api_client import APIClient
from bom_loader import BOMLoaderWindow

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
        self._load_states()

        for filtro in getattr(self, "filter_inputs", []):
            if filtro is None:
                continue
            filtro.textChanged.connect(self._apply_filters)

        self.btn_new.clicked.connect(self.nuovo_codice)
        self.btn_load_bom.clicked.connect(self.apri_carica_distinta)
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
