from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QSlider,
    QHBoxLayout,
    QSpinBox,
    QPushButton,
    QDialogButtonBox,
)


class SettingsDialog(QDialog):
    fontScaleChanged = Signal(float)
    logoutRequested = Signal()

    def __init__(self, font_scale: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni")
        self.resize(380, 200)
        self._building = True

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        intro = QLabel("Modifica le impostazioni dell'interfaccia.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(QLabel("Dimensione testo (%)"))

        row = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(80, 140)
        self.spin = QSpinBox()
        self.spin.setRange(80, 140)
        row.addWidget(self.slider, 1)
        row.addWidget(self.spin)
        layout.addLayout(row)

        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logoutRequested.emit)
        layout.addWidget(logout_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Chiudi")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        value = int(round(font_scale * 100))
        self.slider.setValue(value)
        self.spin.setValue(value)
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        self.slider.valueChanged.connect(self._emit_scale_change)
        self._building = False

    def _emit_scale_change(self, value: int):
        if self._building:
            return
        self.fontScaleChanged.emit(max(80, min(140, value)) / 100)
