import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QInputDialog,
    QTreeWidgetItem,
    QLabel,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QTableWidgetItem,
    QPushButton,
    QCompleter,
)
from PySide6.QtCore import Qt, QStringListModel

from ui_mainwindow import UffTecMainWindowUI
from api_client import APIClient


class UffTecClient(UffTecMainWindowUI):
    def __init__(self):
        super().__init__()
        self.api = APIClient()
        self._open_codes = {}
        self._states = []
        self._form_fields = []
        self._current_detail = None
        self._current_form_revision = None
        self._current_form_editable = False
        self._pending_revision_index = None
        self._all_codes = []
        self._current_files = []
        self._code_model = QStringListModel(self)
        self._code_completer = QCompleter(self._code_model, self)
        self._code_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._code_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._code_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.search_input.setCompleter(self._code_completer)
        self.search_input.textEdited.connect(self._handle_search_text_edited)
        self._code_completer.activated.connect(self._handle_completer_selected)
        self._form_dirty = False
        self._current_nav_key = None

        self._load_states()
        self._load_form_fields()
        self._load_codes_list()
        self._set_empty_detail()

        self.search_input.returnPressed.connect(self._handle_search)
        self.btn_new_code.clicked.connect(self.nuovo_codice)
        self.btn_release.clicked.connect(self._release_current_revision)
        self.btn_new_revision.clicked.connect(self._create_revision)
        self.btn_change_state.clicked.connect(self._change_revision_state)
        self.tabs_list.currentItemChanged.connect(self._handle_tree_selection_changed)
        self.btn_refresh_form.clicked.connect(lambda: self._refresh_form_from_server(force=True))
        self.btn_save_form.clicked.connect(self._save_form_certificazione)
        self.form_table.itemChanged.connect(self._on_form_item_changed)
        self.files_list.filesDropped.connect(self._handle_files_dropped)
        self.side_nav.currentRowChanged.connect(self._handle_side_nav_selection)

    def _load_states(self):
        try:
            self._states = self.api.lista_stati()
        except Exception:
            self._states = [{"name": "concept", "color": "#3498db"}]

    def _load_form_fields(self):
        try:
            self._form_fields = self.api.lista_campi_form()
        except Exception:
            self._form_fields = [
                {"name": "descrizione", "label": "Descrizione"},
                {"name": "quantita", "label": "Quantità"},
                {"name": "ubicazione", "label": "Ubicazione"},
            ]

    def _load_codes_list(self):
        try:
            codici = self.api.lista_codici(include_unreleased=True)
        except Exception:
            codici = []
        codes = sorted({c.get("codice") for c in codici if c.get("codice")})
        self._all_codes = codes
        self._code_model.setStringList(self._all_codes)

    def _add_code_to_completer(self, codice):
        if not codice:
            return
        if codice not in self._all_codes:
            self._all_codes.append(codice)
            self._all_codes.sort()
            self._code_model.setStringList(self._all_codes)

    def _handle_completer_selected(self, text):
        if not text:
            return
        self.search_input.setText(text)
        self._handle_search()

    def _handle_search_text_edited(self, text):
        self._code_completer.setCompletionPrefix(text)
        if text:
            self._code_completer.complete()

    def _handle_search(self):
        codice = self.search_input.text().strip()
        if not codice:
            return

        detail = self._fetch_detail(codice)
        if detail:
            self._add_or_focus_code(detail)
            self._add_code_to_completer(detail.get("codice"))

    def _fetch_detail(self, codice):
        try:
            dettaglio = self.api.dettaglio_codice(codice)
        except Exception as exc:
            QMessageBox.critical(self, "Errore di connessione", str(exc))
            return None

        if not dettaglio:
            QMessageBox.information(self, "Codice non trovato", f"Il codice {codice} non esiste.")
            return None
        return dettaglio

    def _add_or_focus_code(self, codice_data):
        codice = codice_data.get("codice")
        if not codice:
            return

        item = self._open_codes.get(codice)
        if not item:
            item = QTreeWidgetItem([codice])
            self.tabs_list.addTopLevelItem(item)
            self._open_codes[codice] = item
        self._update_code_tree_item(item, codice_data, expand=False)
        self.tabs_list.setCurrentItem(item)

    def _update_code_tree_item(self, item: QTreeWidgetItem, dettaglio, expand: bool = False):
        codice = dettaglio.get("codice", "Codice")
        item.setText(0, codice)
        item.setData(0, Qt.ItemDataRole.UserRole, {"type": "code", "code": codice, "detail": dettaglio})
        item.takeChildren()
        revisioni = sorted(dettaglio.get("revisioni", []), key=lambda r: r.get("indice", 0))
        for rev in revisioni:
            idx = rev.get("indice", 0)
            label = f"rev{idx:02d}"
            child = QTreeWidgetItem([label])
            child.setData(
                0,
                Qt.ItemDataRole.UserRole,
                {
                    "type": "revision",
                    "code": codice,
                    "index": idx,
                    "is_released": rev.get("is_released", False),
                },
            )
            if rev.get("is_released"):
                child.setForeground(0, Qt.GlobalColor.darkGray)
            item.addChild(child)
        item.setExpanded(expand)

    def _handle_tree_selection_changed(self, current, _previous):
        if not current:
            if not self._current_nav_key:
                self._activate_code_center(reset_nav=False)
            self._set_empty_detail()
            return
        data = current.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            self._set_empty_detail()
            return
        self._activate_code_center()
        if data.get("type") == "code":
            detail = data.get("detail")
            self._show_code(detail)
        elif data.get("type") == "revision":
            parent = current.parent()
            if not parent:
                return
            parent_data = parent.data(0, Qt.ItemDataRole.UserRole) or {}
            detail = parent_data.get("detail")
            if detail:
                self._show_code(detail)
                self._handle_form_click(data.get("index"), not data.get("is_released", False))

    def _show_code(self, data):
        if not data:
            self._set_empty_detail()
            return
        self._activate_code_center()
        self._current_detail = data
        self._current_form_revision = None
        codice = data.get("codice") or "Codice sconosciuto"
        descrizione = data.get("descrizione") or ""
        header = f"{codice}"
        if descrizione:
            header = f"{codice} - {descrizione}"
        self.header_label.setText(header)

        revisioni = data.get("revisioni", [])
        self._render_revisions(revisioni)
        self._set_form_panel_state(False)
        self._update_release_button(revisioni)

    def _set_empty_detail(self):
        self._current_detail = None
        self._current_form_revision = None
        self._pending_revision_index = None
        self.header_label.setText("Nessun codice selezionato")
        self._render_revisions([])
        self._set_form_panel_state(False)
        self.btn_release.setEnabled(False)
        self.btn_new_revision.setEnabled(False)
        self.btn_change_state.setEnabled(False)
        if not self._current_nav_key:
            self._activate_code_center(reset_nav=False)

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.deleteLater()

    def _render_revisions(self, revisioni):
        self._clear_layout(self.revisions_layout)
        if not revisioni:
            placeholder = QLabel("Non ci sono revisioni da mostrare.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #6b7280; font-style: italic;")
            self.revisions_layout.addWidget(placeholder)
            self.revisions_layout.addStretch(1)
            return

        for rev in sorted(revisioni, key=lambda r: r.get("indice", 0)):
            wrapper = QFrame()
            wrapper.setObjectName("revisionFrame")
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(12, 8, 12, 8)
            wrapper_layout.setSpacing(4)

            head = QWidget()
            head_layout = QHBoxLayout(head)
            head_layout.setContentsMargins(0, 0, 0, 0)
            head_layout.setSpacing(10)

            rev_label = QLabel(f"rev{rev.get('indice', 0)}")
            rev_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #1f2933;")

            state_label = QLabel(rev.get("stato", "").upper())
            state_label.setProperty("statePill", True)
            bg = rev.get("color") or "#4b5563"
            text_color = self._text_color_for(bg)
            state_label.setStyleSheet(f"background-color: {bg}; color: {text_color};")

            head_layout.addWidget(rev_label)
            head_layout.addWidget(state_label)
            if rev.get("is_released"):
                release_label = QLabel("RILASCIATA")
                release_label.setStyleSheet(
                    "padding: 4px 8px; border-radius: 8px; background-color: #16a34a; color: #fff; font-size: 11px; font-weight: bold;"
                )
                head_layout.addWidget(release_label)
            head_layout.addStretch()
            wrapper_layout.addWidget(head)

            cad_file = rev.get("cad_file")
            if cad_file:
                cad_label = QLabel(f"file CAD: {cad_file}")
                cad_label.setObjectName("cadLabel")
                wrapper_layout.addWidget(cad_label)

            form_button = QPushButton("Form certificazione")
            form_button.setObjectName("formLink")
            form_button.setCursor(Qt.CursorShape.PointingHandCursor)
            form_button.clicked.connect(
                lambda _, idx=rev.get("indice", 0), editable=(not rev.get("is_released")): self._handle_form_click(idx, editable)
            )
            wrapper_layout.addWidget(form_button)

            self.revisions_layout.addWidget(wrapper)

        self.revisions_layout.addStretch(1)

    def _text_color_for(self, color_hex: str) -> str:
        value = color_hex.lstrip("#")
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        try:
            r = int(value[0:2], 16)
            g = int(value[2:4], 16)
            b = int(value[4:6], 16)
        except ValueError:
            return "#ffffff"
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#111111" if luminance > 0.6 else "#ffffff"

    def nuovo_codice(self):
        tipo, ok1 = QInputDialog.getText(self, "Nuovo codice", "Tipo (es. 03):")
        if not ok1 or not tipo.strip():
            return

        stato = self._states[0]["name"] if self._states else None

        try:
            nuovo = self.api.crea_codice(
                tipo.strip(),
                descrizione="",
                quantita=0,
                ubicazione="",
                stato=stato,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile creare il codice:\n{exc}")
            return

        codice_generato = nuovo.get("codice")
        QMessageBox.information(self, "Successo", f"Codice creato: {codice_generato}")

        if codice_generato:
            dettaglio = self._fetch_detail(codice_generato)
            if dettaglio:
                self.search_input.setText(codice_generato)
                self._add_or_focus_code(dettaglio)
                self._add_code_to_completer(codice_generato)
        self.search_input.setFocus()

    def _update_release_button(self, revisioni):
        pending = next((rev for rev in revisioni if not rev.get("is_released")), None)
        self._pending_revision_index = pending.get("indice") if pending else None
        can_release = bool(pending)
        self.btn_release.setEnabled(can_release)
        self.btn_new_revision.setEnabled(bool(self._current_detail) and not can_release)
        self.btn_change_state.setEnabled(can_release)

    def _handle_form_click(self, indice, editable_flag):
        if not self._current_detail:
            return
        self._load_form_fields()
        codice = self._current_detail.get("codice")
        if codice is None:
            return
        can_edit = editable_flag and (self._pending_revision_index == indice)
        self._current_form_revision = {"codice": codice, "indice": indice}
        self._current_form_editable = bool(can_edit)
        titolo = f"Form certificazione rev{indice}"
        self._set_form_panel_state(True, titolo, editable=self._current_form_editable)
        self._refresh_form_from_server(force=True, show_errors=True, bypass_dirty_prompt=True)

    def _populate_form_table(self, campi):
        self.form_table.blockSignals(True)
        self.form_table.setRowCount(0)
        source = campi or [
            {"nome": field.get("name"), "label": field.get("label"), "valore": "", "ordine": pos}
            for pos, field in enumerate(self._form_fields)
        ]
        ordered = sorted(source, key=lambda c: c.get("ordine", 0))
        for idx, campo in enumerate(ordered):
            self.form_table.insertRow(idx)
            label_text = campo.get("label") or campo.get("nome", "") or "Nuova proprietà"
            nome_item = QTableWidgetItem(label_text)
            editable_name = campo.get("editable", False) or not campo.get("nome")
            if not editable_name:
                nome_item.setFlags(nome_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            nome_item.setData(Qt.ItemDataRole.UserRole, campo.get("nome", ""))
            valore_item = QTableWidgetItem(campo.get("valore", ""))
            if not self._current_form_editable:
                valore_item.setFlags(valore_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.form_table.setItem(idx, 0, nome_item)
            self.form_table.setItem(idx, 1, valore_item)
        self.form_table.blockSignals(False)
        self._form_dirty = False


    def _set_form_panel_state(self, enabled: bool, titolo: str | None = None, editable: bool = True):
        self.form_table.setEnabled(enabled)
        self.btn_refresh_form.setEnabled(enabled)
        self.btn_save_form.setEnabled(enabled and editable)
        self.files_list.setEnabled(enabled)
        self.files_list.setDropsEnabled(enabled and editable)
        if not enabled:
            self.form_title.setText("Form certificazione")
            self.form_table.setRowCount(0)
            self._current_form_revision = None
            self._form_dirty = False
            self._current_form_editable = False
            self._clear_file_list()
        else:
            if titolo:
                self.form_title.setText(titolo)
            self._current_form_editable = editable
            self.form_table.setProperty("editable", editable)

    def _save_form_certificazione(self):
        if not self._current_form_revision:
            return
        if self._pending_revision_index is None or self._current_form_revision.get("indice") != self._pending_revision_index:
            QMessageBox.information(self, "Revisione rilasciata", "Non puoi modificare il form di una revisione rilasciata.")
            return
        codice = self._current_form_revision.get("codice")
        indice = self._current_form_revision.get("indice")
        campi = []
        for row in range(self.form_table.rowCount()):
            nome_item = self.form_table.item(row, 0)
            valore_item = self.form_table.item(row, 1)
            nome = ""
            if nome_item:
                nome = nome_item.data(Qt.ItemDataRole.UserRole) or ""
            nome = nome.strip()
            valore = valore_item.text().strip() if valore_item else ""
            if not nome:
                continue
            campi.append({"nome": nome, "valore": valore, "ordine": row})

        try:
            saved = self.api.salva_certificazione(codice, indice, campi)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare il form:\n{exc}")
            return

        if self._current_detail:
            for rev in self._current_detail.get("revisioni", []):
                if rev.get("indice") == indice:
                    rev["certificazione"] = saved
                    break

        self._form_dirty = False
        QMessageBox.information(self, "Salvato", "Form certificazione aggiornato.")

    def _refresh_form_from_server(self, force=False, show_errors=False, bypass_dirty_prompt=False):
        if not self._current_form_revision:
            return
        if not force and self._form_dirty:
            return
        if force and self._form_dirty and not bypass_dirty_prompt:
            confirm = QMessageBox.question(
                self,
                "Conferma aggiornamento",
                "Hai modifiche non salvate. Vuoi sovrascriverle con i dati dal server?",
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        codice = self._current_form_revision.get("codice")
        indice = self._current_form_revision.get("indice")
        if not codice or indice is None:
            return
        try:
            campi = self.api.get_certificazione(codice, indice)
        except Exception as exc:
            if show_errors or force:
                QMessageBox.critical(self, "Errore", f"Impossibile aggiornare il form:\n{exc}")
            return
        self._populate_form_table(campi)
        self._refresh_file_list(show_errors=show_errors)

    def _on_form_item_changed(self, item):
        if not self.form_table.isEnabled() or not self._current_form_editable:
            return
        if item.column() != 1:
            return
        self._form_dirty = True

    def _clear_file_list(self):
        self.files_list.clear()
        self._current_files = []

    def _refresh_file_list(self, show_errors=False):
        if not self._current_form_revision:
            self._clear_file_list()
            return
        codice = self._current_form_revision.get("codice")
        indice = self._current_form_revision.get("indice")
        if not codice or indice is None:
            self._clear_file_list()
            return
        try:
            files = self.api.lista_file_revisione(codice, indice)
        except Exception as exc:
            if show_errors:
                QMessageBox.critical(self, "Errore", f"Impossibile recuperare i file:\n{exc}")
            self._clear_file_list()
            return
        self._current_files = files or []
        self.files_list.clear()
        if not self._current_files:
            placeholder = QListWidgetItem("Nessun file caricato")
            placeholder.setFlags(placeholder.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.files_list.addItem(placeholder)
            return
        for file_info in self._current_files:
            filename = file_info.get("filename", "sconosciuto")
            mimetype = file_info.get("mimetype") or ""
            text = filename if not mimetype else f"{filename} ({mimetype})"
            item = QListWidgetItem(text)
            uploaded = file_info.get("uploaded_at")
            if uploaded:
                item.setToolTip(f"Caricato il {uploaded}")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.files_list.addItem(item)
        self.files_list.setDropsEnabled(self._current_form_editable)

    def _handle_files_dropped(self, paths):
        if not self._current_form_revision or not self._current_form_editable:
            QMessageBox.information(self, "Revisione non modificabile", "Non puoi aggiungere file a questa revisione.")
            return
        codice = self._current_form_revision.get("codice")
        indice = self._current_form_revision.get("indice")
        if not codice or indice is None:
            return
        uploaded = 0
        errors = []
        for raw_path in paths:
            path = Path(raw_path)
            if not path.is_file():
                continue
            try:
                self.api.carica_file_revisione(codice, indice, path)
                uploaded += 1
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        if uploaded:
            self._refresh_file_list(show_errors=True)
            QMessageBox.information(self, "Caricamento completato", f"Caricati {uploaded} file.")
        if errors:
            QMessageBox.warning(self, "Alcuni file non caricati", "\n".join(errors[:5]))

    def _release_current_revision(self):
        if not self._current_detail:
            return
        codice = self._current_detail.get("codice")
        pending_index = self._pending_revision_index
        if not codice or pending_index is None:
            return

        confirm = QMessageBox.question(
            self,
            "Conferma rilascio",
            f"Vuoi rilasciare la revisione {pending_index:02d} del codice {codice}?\nDopo il rilascio sarà in sola lettura.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.api.rilascia_revisione(codice, pending_index)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile rilasciare la revisione:\n{exc}")
            return

        dettaglio = self._fetch_detail(codice)
        if dettaglio:
            self._add_or_focus_code(dettaglio)
            current_item = self.tabs_list.currentItem()
            if current_item:
                current_item.setData(Qt.ItemDataRole.UserRole, dettaglio)
            self._show_code(dettaglio)
            QMessageBox.information(self, "Rilascio completato", f"La revisione {pending_index:02d} è stata rilasciata.")

    def _create_revision(self):
        if not self._current_detail:
            QMessageBox.information(self, "Nessun codice", "Apri prima un codice per creare una revisione.")
            return

        codice = self._current_detail.get("codice")
        if not codice:
            return

        if self._pending_revision_index is not None:
            QMessageBox.warning(self, "Revisione esistente", "Esiste già una revisione non rilasciata. Rilasciarla prima di crearne una nuova.")
            return

        stato = self._state_for_new_revision()

        try:
            nuova_rev = self.api.crea_revisione(codice, stato)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile creare la revisione:\n{exc}")
            return

        dettaglio = self._fetch_detail(codice)
        if dettaglio:
            self._current_detail = dettaglio
            current_item = self.tabs_list.currentItem()
            if current_item:
                current_item.setData(Qt.ItemDataRole.UserRole, dettaglio)
            self._show_code(dettaglio)
            indice = nuova_rev.get("indice", self._pending_revision_index)
            if indice is not None:
                self._handle_form_click(indice, True)
        QMessageBox.information(self, "Revisione creata", "È stata creata una nuova revisione.")

    def _state_for_new_revision(self):
        states = [s["name"] for s in self._states if s.get("name")]
        default_state = states[0] if states else None
        if not self._current_detail:
            return default_state
        revisioni = self._current_detail.get("revisioni", [])
        if not revisioni:
            return default_state
        last_rev = max(revisioni, key=lambda r: r.get("indice", 0))
        return last_rev.get("stato") or default_state

    def _change_revision_state(self):
        if not self._current_detail or self._pending_revision_index is None:
            QMessageBox.information(self, "Nessuna revisione aperta", "Non ci sono revisioni modificabili.")
            return

        stato_corrente = None
        for rev in self._current_detail.get("revisioni", []):
            if rev.get("indice") == self._pending_revision_index:
                stato_corrente = rev.get("stato")
                break

        if not stato_corrente:
            QMessageBox.warning(self, "Stato sconosciuto", "Stato corrente non disponibile.")
            return

        state_names = [s["name"] for s in self._states if s.get("name")]
        if not state_names:
            QMessageBox.warning(self, "Stati non configurati", "Lista stati vuota.")
            return

        try:
            current_idx = state_names.index(stato_corrente)
        except ValueError:
            current_idx = -1

        allowed = state_names[current_idx + 1 :] if current_idx + 1 < len(state_names) else []
        if not allowed:
            QMessageBox.information(self, "Stato finale", "La revisione è già nell'ultimo stato disponibile.")
            return

        nuovo_stato, ok = QInputDialog.getItem(
            self,
            "Cambio stato revisione",
            "Seleziona il prossimo stato:",
            allowed,
            0,
            False,
        )
        if not ok or not nuovo_stato:
            return

        codice = self._current_detail.get("codice")
        if not codice:
            return

        try:
            self.api.cambia_stato_revisione(codice, self._pending_revision_index, nuovo_stato)
        except Exception as exc:
            QMessageBox.critical(self, "Errore", f"Impossibile cambiare stato:\n{exc}")
            return

        dettaglio = self._fetch_detail(codice)
        if dettaglio:
            self._current_detail = dettaglio
            current_item = self.tabs_list.currentItem()
            if current_item:
                current_item.setData(Qt.ItemDataRole.UserRole, dettaglio)
            self._show_code(dettaglio)
            self._handle_form_click(self._pending_revision_index, True)

    def _handle_side_nav_selection(self, row):
        if row is None or row < 0:
            self._current_nav_key = None
            return
        item = self.side_nav.item(row)
        if not item:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        widget = getattr(self, "side_nav_pages", {}).get(key)
        if not widget:
            return
        stack = getattr(self, "center_stack", None)
        if stack:
            stack.setCurrentWidget(widget)
        self._current_nav_key = key
        self.tabs_list.blockSignals(True)
        self.tabs_list.clearSelection()
        self.tabs_list.blockSignals(False)
        self._set_empty_detail()

    def _activate_code_center(self, reset_nav: bool = True):
        stack = getattr(self, "center_stack", None)
        code_page = getattr(self, "code_page", None)
        if stack and code_page:
            stack.setCurrentWidget(code_page)
        if reset_nav:
            self._clear_side_nav_selection()

    def _clear_side_nav_selection(self):
        nav = getattr(self, "side_nav", None)
        if not nav:
            return
        nav.blockSignals(True)
        nav.setCurrentRow(-1)
        nav.clearSelection()
        nav.blockSignals(False)
        self._current_nav_key = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UffTecClient()
    window.showMaximized()
    sys.exit(app.exec())
