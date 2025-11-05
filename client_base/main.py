import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from ui_mainwindow import MainWindowUI
from api_client import APIClient

class PLMClient(MainWindowUI):
    def __init__(self):
        super().__init__()
        self.api = APIClient()
        self.btn_refresh.clicked.connect(self.carica_lista)
        self.btn_search.clicked.connect(self.cerca_codice)
        self.btn_new.clicked.connect(self.nuovo_codice)
        self.carica_lista()  # carica all'avvio
        

    def carica_lista(self):
        try:
            codici = self.api.lista_codici()
            self.table.setRowCount(len(codici))
            for i, c in enumerate(codici):
                self.table.setItem(i, 0, self._item(c["codice"]))
                self.table.setItem(i, 1, self._item(c["descrizione"]))
                self.table.setItem(i, 2, self._item(str(c["quantita"])))
                self.table.setItem(i, 3, self._item(c["ubicazione"]))
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore di connessione:\n{e}")

    def cerca_codice(self):
        codice = self.input_search.text().strip()
        if not codice:
            QMessageBox.warning(self, "Attenzione", "Inserisci un codice da cercare.")
            return
        try:
            c = self.api.cerca_codice(codice)
            if not c:
                QMessageBox.information(self, "Risultato", f"Nessun codice trovato: {codice}")
                return
            self.table.setRowCount(1)
            self.table.setItem(0, 0, self._item(c["codice"]))
            self.table.setItem(0, 1, self._item(c["descrizione"]))
            self.table.setItem(0, 2, self._item(str(c["quantita"])))
            self.table.setItem(0, 3, self._item(c["ubicazione"]))
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
