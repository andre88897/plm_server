from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget
)

class MainWindowUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PLM Client - Magazzino")
        self.resize(700, 400)

        layout = QVBoxLayout(self)

        # --- Barra superiore ---
        top_bar = QHBoxLayout()
        self.btn_new = QPushButton("Nuovo codice")
        top_bar.addWidget(self.btn_new)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # --- Tabella ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        headers = ["Codice", "Descrizione", "Quantità", "Ubicazione"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(1)

        # riga 0 riservata ai filtri colonna per colonna
        self.filter_inputs = []
        for col, header in enumerate(headers):
            filtro = QLineEdit()
            filtro.setPlaceholderText(f"Filtro {header.lower()}...")
            filtro.setClearButtonEnabled(True)
            self.table.setCellWidget(0, col, filtro)
            self.filter_inputs.append(filtro)

        layout.addWidget(self.table)
