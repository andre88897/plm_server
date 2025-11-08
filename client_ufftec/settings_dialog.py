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
        self.resize(420, 220)
        self._building = True
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        intro = QLabel("Personalizza il client. Le modifiche alla dimensione del testo si applicano subito.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(QLabel("Dimensione testo (%)"))

        control_row = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(80, 140)
        self.spin = QSpinBox()
        self.spin.setRange(80, 140)
        control_row.addWidget(self.slider, 1)
        control_row.addWidget(self.spin)
        layout.addLayout(control_row)

        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("logoutButton")
        layout.addWidget(logout_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        button_box.button(QDialogButtonBox.StandardButton.Close).setText("Chiudi")
        layout.addWidget(button_box)

        value = int(round(font_scale * 100))
        self.slider.setValue(value)
        self.spin.setValue(value)
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        self.slider.valueChanged.connect(self._emit_scale_change)
        logout_btn.clicked.connect(self.logoutRequested.emit)
        self._building = False

    def _emit_scale_change(self, value: int):
        if self._building:
            return
        self.fontScaleChanged.emit(max(80, min(140, value)) / 100)
