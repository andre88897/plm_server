import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from ui_mainwindow import MainWindowUI
from api_client import APIClient

class PLMClient(MainWindowUI):
    def __init__(self):
        super().__init__()
        self.api = APIClient()
        self._codici_cache = []

        for filtro in getattr(self, "filter_inputs", []):
            filtro.textChanged.connect(self._apply_filters)

        self.btn_new.clicked.connect(self.nuovo_codice)
        self.carica_lista()  # carica all'avvio
        

    def carica_lista(self):
        try:
            codici = self.api.lista_codici()
            self._codici_cache = codici
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

        try:
            nuovo = self.api.crea_codice(tipo.strip(), descrizione, quantita, ubicazione)
            QMessageBox.information(self, "Successo", f"Codice generato: {nuovo['codice']}")
            self.carica_lista()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile creare codice:\n{e}")

    
    def _apply_filters(self, *_):
        filtri = [f.text().strip().lower() for f in getattr(self, "filter_inputs", [])]
        filtrati = []

        for codice in self._codici_cache:
            valori = [
                str(codice.get("codice", "")),
                str(codice.get("descrizione", "")),
                str(codice.get("quantita", "")),
                str(codice.get("ubicazione", "")),
            ]

            if all((not filtro) or filtro in valore.lower() for filtro, valore in zip(filtri, valori)):
                filtrati.append(codice)

        self._mostra_codici(filtrati)


    def _mostra_codici(self, codici):
        # prima riga riservata ai filtri
        offset = 1
        self.table.setRowCount(len(codici) + offset)

        for row_index, codice in enumerate(codici, start=offset):
            self.table.setItem(row_index, 0, self._item(codice.get("codice", "")))
            self.table.setItem(row_index, 1, self._item(codice.get("descrizione", "")))
            self.table.setItem(row_index, 2, self._item(str(codice.get("quantita", ""))))
            self.table.setItem(row_index, 3, self._item(codice.get("ubicazione", "")))


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
