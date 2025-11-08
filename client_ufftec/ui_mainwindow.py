from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QToolButton,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QStackedWidget,
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PySide6.QtCore import Qt, QSize, Signal


class UffTecMainWindowUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PLM Client - Ufficio Tecnico")
        self.resize(1280, 720)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Top bar stile FreeCAD ---
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(68)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 10, 20, 10)
        top_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cerca codice...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setObjectName("searchInput")
        top_layout.addWidget(self.search_input, 4)

        button_bar = QHBoxLayout()
        button_bar.setContentsMargins(0, 0, 0, 0)
        button_bar.setSpacing(8)

        self.btn_new_code = self._build_toolbar_button(
            object_name="btnNewCode",
            icon=self._build_new_code_icon(),
            tooltip="Nuovo codice",
        )
        button_bar.addWidget(self.btn_new_code)

        self.btn_release = self._build_toolbar_button(
            object_name="btnRelease",
            icon=self._build_release_icon(),
            tooltip="Rilascia revisione aperta",
        )
        self.btn_release.setEnabled(False)
        button_bar.addWidget(self.btn_release)

        self.btn_new_revision = self._build_toolbar_button(
            object_name="btnNewRevision",
            icon=self._build_revision_icon(),
            tooltip="Crea nuova revisione",
        )
        self.btn_new_revision.setEnabled(False)
        button_bar.addWidget(self.btn_new_revision)

        self.btn_change_state = self._build_toolbar_button(
            object_name="btnChangeState",
            icon=self._build_change_state_icon(),
            tooltip="Cambia stato revisione",
        )
        self.btn_change_state.setEnabled(False)
        button_bar.addWidget(self.btn_change_state)

        self.btn_settings = self._build_toolbar_button(
            object_name="btnSettings",
            icon=self._build_settings_icon(),
            tooltip="Impostazioni",
        )
        button_bar.addWidget(self.btn_settings)

        top_layout.addLayout(button_bar, 1)

        root_layout.addWidget(top_bar)

        # --- Main area split in three sections ---
        main_area = QFrame()
        main_layout = QHBoxLayout(main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Tabs column
        tabs_panel = QFrame()
        tabs_panel.setObjectName("tabsPanel")
        tabs_panel.setFixedWidth(240)
        tabs_layout = QVBoxLayout(tabs_panel)
        tabs_layout.setContentsMargins(12, 12, 12, 12)
        tabs_layout.setSpacing(8)

        self.tabs_list = QTreeWidget()
        self.tabs_list.setObjectName("tabsList")
        self.tabs_list.setAlternatingRowColors(True)
        self.tabs_list.setHeaderHidden(True)
        tabs_layout.addWidget(self.tabs_list, 7)

        self.side_nav = QListWidget()
        self.side_nav.setObjectName("sideNav")
        self.side_nav.setAlternatingRowColors(True)
        self.side_nav.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.side_nav_entries = []
        self.side_nav_items = {}
        self.side_nav_labels = {}
        for label in ("Home", "Lavori", "Progetti", "Colleghi"):
            key = label.lower()
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.side_nav.addItem(item)
            self.side_nav_entries.append((key, label))
            self.side_nav_items[key] = item
            self.side_nav_labels[key] = label
        self.side_nav.setCurrentRow(-1)
        self.side_nav.clearSelection()
        tabs_layout.addWidget(self.side_nav, 3)

        main_layout.addWidget(tabs_panel)

        # Center area
        center_panel = QFrame()
        center_panel.setObjectName("centerPanel")
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(30, 30, 30, 30)
        center_layout.setSpacing(16)

        self.center_stack = QStackedWidget()
        self.center_stack.setObjectName("centerStack")

        self.code_page = QWidget()
        self.code_page.setObjectName("codePage")
        code_page_layout = QVBoxLayout(self.code_page)
        code_page_layout.setContentsMargins(0, 0, 0, 0)
        code_page_layout.setSpacing(16)

        self.header_label = QLabel("Nessun codice selezionato")
        self.header_label.setObjectName("codeLabel")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_font = self.header_label.font()
        header_font.setPointSize(30)
        header_font.setBold(True)
        self.header_label.setFont(header_font)
        code_page_layout.addWidget(self.header_label)

        self.revisions_widget = QWidget()
        self.revisions_widget.setObjectName("revisionsWidget")
        self.revisions_layout = QVBoxLayout(self.revisions_widget)
        self.revisions_layout.setContentsMargins(10, 10, 10, 10)
        self.revisions_layout.setSpacing(8)
        code_page_layout.addWidget(self.revisions_widget, 1)

        self.center_stack.addWidget(self.code_page)
        self.side_nav_pages = {}
        for key, label in self.side_nav_entries:
            placeholder = self._build_center_placeholder(label)
            placeholder.setObjectName(f"{key}CenterView")
            self.center_stack.addWidget(placeholder)
            self.side_nav_pages[key] = placeholder

        center_layout.addWidget(self.center_stack, 1)

        main_layout.addWidget(center_panel, 1)

        # Right placeholder
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_panel.setMinimumWidth(320)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(12)

        self.form_title = QLabel("Form certificazione")
        self.form_title.setObjectName("formTitle")
        title_font = self.form_title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.form_title.setFont(title_font)
        right_layout.addWidget(self.form_title)

        self.form_table = QTableWidget(0, 2)
        self.form_table.setObjectName("formTable")
        self.form_table.setHorizontalHeaderLabels(["Proprietà", "Valore"])
        self.form_table.horizontalHeader().setStretchLastSection(True)
        self.form_table.verticalHeader().setVisible(False)
        self.form_table.setEnabled(False)
        right_layout.addWidget(self.form_table, 1)

        form_buttons = QHBoxLayout()
        form_buttons.setSpacing(8)
        self.btn_refresh_form = QPushButton("Aggiorna")
        self.btn_refresh_form.setObjectName("btnRefreshForm")
        self.btn_refresh_form.setEnabled(False)
        form_buttons.addWidget(self.btn_refresh_form)

        self.btn_save_form = QPushButton("Salva")
        self.btn_save_form.setObjectName("btnSaveForm")
        self.btn_save_form.setEnabled(False)
        form_buttons.addWidget(self.btn_save_form)
        form_buttons.addStretch()

        right_layout.addLayout(form_buttons)

        self.files_label = QLabel("File revisione")
        self.files_label.setObjectName("filesLabel")
        right_layout.addWidget(self.files_label)

        self.files_list = FileDropList()
        self.files_list.setObjectName("filesList")
        self.files_list.setEnabled(False)
        right_layout.addWidget(self.files_list, 1)

        main_layout.addWidget(right_panel)

        root_layout.addWidget(main_area, 1)

        self.setStyleSheet(
            """
            #topBar {
                background-color: #2f3b4d;
                border-bottom: 2px solid #19202a;
            }
            #searchInput {
                border: 1px solid #445261;
                border-radius: 6px;
                padding: 8px 12px;
                background-color: #fdfdfd;
                font-size: 16px;
            }
            #btnNewCode {
                background-color: #f0f5ff;
                border: 1px solid #a3c0ff;
                border-radius: 50%;
                padding: 10px;
            }
            #btnNewCode:hover {
                background-color: #dae8ff;
            }
            #btnRelease {
                background-color: #fff4ec;
                border: 1px solid #f5b98a;
                border-radius: 50%;
                padding: 10px;
            }
            #btnRelease:disabled {
                background-color: #f5f5f5;
                border-color: #dddddd;
            }
            #btnRelease:hover:enabled {
                background-color: #ffe5d2;
            }
            #btnNewRevision {
                background-color: #fff8d6;
                border: 1px solid #fcd34d;
                border-radius: 50%;
                padding: 10px;
            }
            #btnNewRevision:disabled {
                background-color: #f5f5f5;
                border-color: #dddddd;
            }
            #btnNewRevision:hover:enabled {
                background-color: #ffeeba;
            }
            #btnChangeState {
                background-color: #e0f2fe;
                border: 1px solid #38bdf8;
                border-radius: 50%;
                padding: 10px;
            }
            #btnChangeState:disabled {
                background-color: #f5f5f5;
                border-color: #dddddd;
            }
            #btnChangeState:hover:enabled {
                background-color: #bae6fd;
            }
            #btnSettings {
                background-color: #f3f4f6;
                border: 1px solid #cbd5f5;
                border-radius: 50%;
                padding: 10px;
            }
            #btnSettings:hover {
                background-color: #e5e7eb;
            }
            #tabsPanel {
                background-color: #f5f7fa;
                border-right: 1px solid #d9dfe7;
            }
            #tabsList {
                border: 1px solid #c8d0dc;
                border-radius: 6px;
                background-color: #fff;
            }
            #sideNav {
                border: 1px solid #c8d0dc;
                border-radius: 6px;
                background-color: #fff;
            }
            #sideNav::item {
                padding: 6px 10px;
            }
            #sideNav::item:selected {
                background-color: #e0e7ff;
                color: #1d4ed8;
                font-weight: bold;
            }
            #centerStack {
                border: none;
            }
            #centerPanel {
                background-color: #ffffff;
            }
            #revisionsWidget {
                border: 1px solid #e3e7ef;
                border-radius: 12px;
                background-color: #fbfbfe;
            }
            QFrame#revisionFrame {
                border-bottom: 1px solid #e6e9f2;
            }
            #rightPanel {
                background-color: #f0f0f4;
                border-left: 1px dashed #d0d0d8;
            }
            #formTitle {
                color: #1f2a37;
            }
            #formTable {
                background-color: #ffffff;
                border: 1px solid #d9dfe7;
                border-radius: 8px;
            }
            #filesLabel {
                color: #1f2a37;
                font-weight: bold;
            }
            #filesList {
                background-color: #ffffff;
                border: 1px dashed #cbd5f5;
                border-radius: 8px;
                min-height: 120px;
            }
            #btnRefreshForm, #btnSaveForm {
                padding: 8px 12px;
                border-radius: 6px;
            }
            #btnRefreshForm {
                background-color: #e2e8f0;
                border: 1px solid #cbd5f5;
                color: #1e293b;
                font-weight: 600;
            }
            #btnRefreshForm:disabled {
                background-color: #f4f4f6;
                border-color: #e0e0e0;
                color: #9da3af;
            }
            #btnSaveForm {
                background-color: #0ea5e9;
                border: none;
                color: #fff;
                font-weight: bold;
            }
            #btnSaveForm:disabled {
                background-color: #9ca3af;
            }
            #codeLabel {
                color: #1d2a3a;
                letter-spacing: 2px;
            }
            QLabel[statePill="true"] {
                padding: 4px 10px;
                border-radius: 12px;
                color: #fff;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QLabel#cadLabel {
                color: #4a5568;
                font-style: italic;
                margin-left: 24px;
            }
            QPushButton#formLink {
                color: #2563eb;
                border: none;
                background: transparent;
                text-align: left;
                padding: 0;
                font-weight: 600;
            }
            QPushButton#formLink:hover {
                text-decoration: underline;
            }
            """
        )

    def _build_toolbar_button(self, *, object_name, icon, tooltip):
        button = QToolButton()
        button.setObjectName(object_name)
        button.setIcon(icon)
        button.setIconSize(QSize(28, 28))
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        return button

    def _build_new_code_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QColor("#2ecc71"))
        painter.setPen(QColor("#27ae60"))
        painter.drawRoundedRect(2, 2, 28, 28, 8, 8)

        painter.setBrush(Qt.GlobalColor.transparent)
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawLine(16, 8, 16, 24)
        painter.drawLine(8, 16, 24, 16)
        painter.end()

        return QIcon(pixmap)

    def _build_center_placeholder(self, title: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        layout.addStretch(1)

        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_font = label.font()
        label_font.setPointSize(28)
        label_font.setBold(True)
        label.setFont(label_font)
        label.setStyleSheet("color: #1f2937;")
        layout.addWidget(label)

        subtitle = QLabel("Contenuti in arrivo")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #64748b; font-size: 16px;")
        layout.addWidget(subtitle)

        layout.addStretch(1)
        return widget

    def _build_release_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#f97316"))
        painter.setPen(QColor("#ea580c"))
        painter.drawEllipse(2, 2, 28, 28)

        pen = QPen(QColor("#ffffff"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(10, 16, 15, 21)
        painter.drawLine(15, 21, 22, 11)
        painter.end()

        return QIcon(pixmap)

    def _build_revision_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#facc15"))
        painter.setPen(QColor("#eab308"))
        painter.drawRoundedRect(2, 2, 28, 28, 10, 10)

        pen = QPen(QColor("#92400e"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(10, 10, 22, 10)
        painter.drawLine(12, 10, 12, 22)
        painter.drawLine(12, 22, 22, 22)
        painter.end()

        return QIcon(pixmap)

    def _build_change_state_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#38bdf8"))
        painter.setPen(QColor("#0ea5e9"))
        painter.drawEllipse(2, 2, 28, 28)

        pen = QPen(QColor("#ffffff"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(10, 16, 22, 16)
        painter.drawLine(16, 10, 22, 16)
        painter.drawLine(16, 22, 22, 16)
        painter.end()

        return QIcon(pixmap)

    def _build_settings_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#4b5563"))
        painter.setPen(Qt.GlobalColor.transparent)
        painter.drawEllipse(6, 6, 20, 20)

        pen = QPen(QColor("#ffffff"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(12, 12, 8, 8)

        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        for angle in range(0, 360, 45):
            painter.save()
            painter.translate(16, 16)
            painter.rotate(angle)
            painter.drawLine(0, -10, 0, -13)
            painter.restore()

        painter.end()
        return QIcon(pixmap)


class FileDropList(QListWidget):
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drops_enabled = False
        self.setAlternatingRowColors(True)
        self.setAcceptDrops(False)

    def setDropsEnabled(self, enabled: bool):
        self._drops_enabled = enabled
        self.setAcceptDrops(enabled)

    def dragEnterEvent(self, event):
        if self._drops_enabled and event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._drops_enabled and event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self._drops_enabled or not event.mimeData().hasUrls():
            event.ignore()
            return
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        if paths:
            self.filesDropped.emit(paths)
        event.acceptProposedAction()
