from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel
)

class MainWindowUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PLM Client - Magazzino")
        self.resize(700, 400)

        layout = QVBoxLayout(self)

        # --- Barra superiore ---
        top_bar = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Cerca codice...")
        self.btn_search = QPushButton("Cerca")
        self.btn_refresh = QPushButton("Aggiorna")
        self.btn_new = QPushButton("Nuovo codice")
        top_bar.addWidget(self.btn_new)
        top_bar.addWidget(QLabel("Codice:"))
        top_bar.addWidget(self.input_search)
        top_bar.addWidget(self.btn_search)
        top_bar.addWidget(self.btn_refresh)
        layout.addLayout(top_bar)

        # --- Tabella ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Codice", "Descrizione", "Quantità", "Ubicazione"])
        layout.addWidget(self.table)
