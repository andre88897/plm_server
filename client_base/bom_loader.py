from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox
)
from PySide6.QtGui import QFont


class BOMLoaderWindow(QDialog):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api = api_client
        self._row_buttons = {}

        self.setWindowTitle("Carica distinta")
        self.resize(650, 400)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.btn_send_all = QPushButton("Invia tutte")
        self.btn_add_row = QPushButton("Aggiungi riga")
        controls.addWidget(self.btn_send_all)
        controls.addWidget(self.btn_add_row)
        controls.addStretch()
        layout.addLayout(controls)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Codice padre", "Codice figlio", "Quantità", "Azioni"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setRowCount(0)
        layout.addWidget(self.table)

        self.btn_send_all.clicked.connect(self._send_all)
        self.btn_add_row.clicked.connect(self._add_row)

        for _ in range(5):
            self._add_row()

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)

        for col in range(3):
            item = QTableWidgetItem("")
            self.table.setItem(row, col, item)

        btn_invia = QPushButton("Invia")
        btn_invia.clicked.connect(lambda _, r=row: self._send_row(r))
        self.table.setCellWidget(row, 3, btn_invia)
        self._row_buttons[row] = btn_invia

    def _row_has_data(self, row):
        padre_item = self.table.item(row, 0)
        figlio_item = self.table.item(row, 1)
        return bool(padre_item and padre_item.text().strip() and figlio_item and figlio_item.text().strip())

    def _send_row(self, row, *, batch=False):
        if row not in self._row_buttons:
            return False

        button = self._row_buttons[row]
        if not button.isEnabled():
            return False

        padre = self.table.item(row, 0).text().strip() if self.table.item(row, 0) else ""
        figlio = self.table.item(row, 1).text().strip() if self.table.item(row, 1) else ""
        quantita_text = self.table.item(row, 2).text().strip() if self.table.item(row, 2) else ""

        if not padre or not figlio:
            if not batch:
                QMessageBox.warning(self, "Campi mancanti", "Compila codice padre e figlio prima di inviare la riga.")
            return False

        if not quantita_text:
            if not batch:
                QMessageBox.warning(self, "Campi mancanti", "Inserisci la quantità per la riga selezionata.")
            return False

        try:
            quantita = float(quantita_text)
        except ValueError:
            QMessageBox.warning(self, "Quantità non valida", "La quantità deve essere un numero.")
            return False

        try:
            self.api.aggiungi_componente(padre, figlio, quantita)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile inviare la riga:\n{exc}")
            return False

        self._mark_row_sent(row)
        parent = self.parent()
        if parent and hasattr(parent, "on_bom_row_sent"):
            parent.on_bom_row_sent(padre)
        return True

    def _mark_row_sent(self, row):
        for col in range(3):
            item = self.table.item(row, col)
            if not item:
                continue
            font = QFont(item.font())
            font.setBold(True)
            item.setFont(font)

        button = self._row_buttons.get(row)
        if button:
            button.setEnabled(False)
            button.setText("Inviata")

    def _send_all(self):
        sent = 0
        for row in range(self.table.rowCount()):
            if not self._row_has_data(row):
                continue
            if self._send_row(row, batch=True):
                sent += 1

        if sent:
            QMessageBox.information(self, "Distinta inviata", f"Righe inviate: {sent}")
        else:
            QMessageBox.information(self, "Nessuna riga", "Non ci sono righe valide da inviare.")
