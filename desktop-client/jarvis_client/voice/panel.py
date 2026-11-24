from dataclasses import replace

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                              QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from jarvis_client.voice.audio import AudioDeviceManager
from jarvis_client.voice.manager import VoiceConversationManager
from jarvis_client.voice.settings import VoiceSettingsManager, installed_stt_models, model_directory
from jarvis_client.voice.shortcuts import VoiceShortcuts


class VoicePanel(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.store = VoiceSettingsManager(window.store.directory)
        self.manager = VoiceConversationManager(self.store.load(), self)
        self.shortcuts = VoiceShortcuts(window, window.voice_ptt, window.voice_stop)
        self.shortcuts.configure(self.manager.settings)
        layout = QVBoxLayout(self)
        heading = QLabel("Praat met JARVIS")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        self.status = QLabel("Klaar om te luisteren")
        self.status.setObjectName("heading")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.microphone_status = QLabel("Microfoon uit")
        self.microphone_status.setObjectName("muted")
        self.microphone_status.setWordWrap(True)
        layout.addWidget(self.microphone_status)
        self.level = QProgressBar()
        self.level.setRange(0, 100)
        self.level.setValue(0)
        self.level.setTextVisible(False)
        self.level.setMaximumHeight(10)
        layout.addWidget(self.level)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        self.error.setObjectName("notice")
        self.error.hide()
        layout.addWidget(self.error)
        self.consent = QCheckBox("Mijn gekozen microfoon gebruiken · toestemming onthouden")
        self.consent.setChecked(self.manager.settings.microphone_allowed)
        self.consent.toggled.connect(self.permission_changed)
        controls = QHBoxLayout()
        self.ptt = QPushButton("●  Start luisteren")
        self.ptt.setObjectName("primary")
        self.ptt.setMinimumHeight(55)
        self.ptt.clicked.connect(window.voice_ptt)
        controls.addWidget(self.ptt, 1)
        sample = QPushButton("Stemvoorbeeld afspelen")
        sample.clicked.connect(self.manager.sample)
        controls.addWidget(sample)
        stop = QPushButton("■  Stop alles")
        stop.clicked.connect(window.voice_stop)
        controls.addWidget(stop)
        layout.addLayout(controls)
        takeover=QPushButton("Gesprek hier overnemen")
        takeover.setToolTip("Selecteer eerst een eerder gesprek bij Gesprekken. Neem daarna expliciet de spraaksessie van een ander apparaat over.")
        takeover.clicked.connect(lambda:window.voice_session.takeover())
        layout.addWidget(takeover)
        self.wake = QCheckBox("Luister naar Hé JARVIS")
        self.wake.setToolTip("Experimentele lokale herkenning na je hele zin; standaard uit. Microfoon is actief zolang je dit inschakelt.")
        self.wake.toggled.connect(self.set_wake)
        layout.addWidget(self.wake)
        self.transcript, self.answer = QPlainTextEdit(), QPlainTextEdit()
        for box, title, placeholder in ((self.transcript, "JIJ", "Wat ik heb verstaan…"), (self.answer, "JARVIS", "Mijn antwoord…")):
            title_label = QLabel(title)
            title_label.setObjectName("eyebrow")
            layout.addWidget(title_label)
            box.setReadOnly(True)
            box.setPlaceholderText(placeholder)
            if box is self.transcript:
                box.setMaximumHeight(90)
                layout.addWidget(box)
            else:
                layout.addWidget(box, 1)
        self.settings_toggle = QToolButton()
        self.settings_toggle.setText("Stem en microfoon instellen  ▾")
        self.settings_toggle.setCheckable(True)
        layout.addWidget(self.settings_toggle)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVisible(False)
        self.settings_toggle.toggled.connect(scroll.setVisible)
        settings_widget = QWidget()
        form = QFormLayout(settings_widget)
        self.inputs, self.outputs = QComboBox(), QComboBox()
        for combo, key in ((self.inputs, "input_device"), (self.outputs, "output_device")):
            combo.addItem("Windows-standaard", -1)
            selected = getattr(self.manager.settings, key)
            if selected >= 0:
                combo.addItem(f"Opgeslagen apparaat {selected} · vernieuw om de naam te controleren", selected)
                combo.setCurrentIndex(1)
        # Device enumeration is explicit and runs outside the GUI thread.
        refresh = QPushButton("Audioapparaten vernieuwen")
        refresh.clicked.connect(self.refresh_devices)
        form.addRow(refresh)
        form.addRow("Microfoon", self.inputs)
        form.addRow("Luidspreker", self.outputs)
        form.addRow(self.consent)
        self.inputs.activated.connect(lambda: self.save_device("input_device", self.inputs))
        self.outputs.activated.connect(lambda: self.save_device("output_device", self.outputs))
        self.fields = {}
        settings = self.manager.settings
        for key, title, low, high, step in (("input_gain", "Invoerversterking", .1, 3, .1), ("output_gain", "Uitvoervolume", 0, 1, .1),
                                          ("sensitivity", "Spraakgevoeligheid", 0, 1, .05), ("silence_seconds", "Stilte tot einde opname (s)", .4, 4, .2),
                                          ("speed", "Spreeksnelheid", .7, 1.5, .05)):
            field = QDoubleSpinBox()
            field.setRange(low, high)
            field.setSingleStep(step)
            field.setValue(getattr(settings, key))
            self.fields[key] = field
            form.addRow(title, field)
        for key, title, low, high in (("max_seconds", "Maximale opname (s)", 5, 120), ("followup_seconds", "Vervolgvraagvenster (0 = uit)", 0, 30), ("speaker", "Piper stemprofiel (0–51)", 0, 51)):
            field = QSpinBox()
            field.setRange(low, high)
            field.setValue(getattr(settings, key))
            self.fields[key] = field
            form.addRow(title, field)
        self.choices = {}
        for key, title, choices in (("model", "Whisper-model", [("Small · geïnstalleerd indien gedownload", "whisper-small"), ("Base · aparte installatie nodig", "whisper-base"), ("Tiny · aparte installatie nodig", "whisper-tiny")]),
                                    ("device", "Rekenapparaat", [("Automatisch · GPU met CPU-fallback", "auto"), ("CPU int8", "cpu"), ("CUDA met CPU-fallback", "cuda")]),
                                    ("profile", "Geheugenprofiel", [("Desktop", "desktop"), ("Licht · één engine in geheugen", "light")]),
                                    ("provider", "Stemengine", [("Piper · Nederlands · lokaal", "piper")]),
                                    ("voice", "Nederlandse stem", [("Ronnie · één stem · aanbevolen", "ronnie"), ("MLS · 52 profielen · experimenteel", "mls")])):
            field = QComboBox()
            for text, value in choices:
                field.addItem(text, value)
            field.setCurrentIndex(field.findData(getattr(settings, key)))
            self.choices[key] = field
            form.addRow(title, field)
        self.paths = QLineEdit(settings.models)
        self.paths.setPlaceholderText(model_directory(settings))
        self.paths.editingFinished.connect(self.refresh_models)
        form.addRow("Lokale modelmap", self.paths)
        self.ptt_key = QLineEdit(settings.ptt_shortcut)
        self.stop_key = QLineEdit(settings.stop_shortcut)
        form.addRow("Sneltoets spreken", self.ptt_key)
        form.addRow("Sneltoets direct stoppen", self.stop_key)
        self.global_keys = QCheckBox("Ik schakel globale sneltoetsen in voor deze appsessie")
        form.addRow(self.global_keys)
        self.cache = QCheckBox("Begrensde audio-cache in geheugen (8 MB; geen audiobestanden)")
        self.cache.setChecked(settings.cache)
        form.addRow(self.cache)
        save = QPushButton("Spraakinstellingen toepassen en opslaan")
        save.clicked.connect(self.save)
        form.addRow(save)
        limitation = QLabel("XTTS v2 is niet geïnstalleerd: aparte grote runtime/modellen, CPML-licentie en een toegestane referentiestem zijn nodig. Piper is de beschikbare lokale stem. Stoppen werkt via knop of sneltoets; spraakgestuurd onderbreken is zonder echo-onderdrukking niet beschikbaar.")
        limitation.setWordWrap(True)
        form.addRow(limitation)
        scroll.setWidget(settings_widget)
        layout.addWidget(scroll, 1)
        self.timings = QLabel("")
        self.timings.setWordWrap(True)
        form.addRow(self.timings)
        self.manager.changed.connect(self.changed)
        self.manager.problem.connect(self.show_problem)
        self.manager.transcript.connect(self.transcript.setPlainText)
        self.manager.answer.connect(self.answer.setPlainText)
        self.manager.metrics.connect(self.show_timings)
        self.manager.level.connect(lambda level: self.level.setValue(round(level * 100)))
        self.manager.ready_text.connect(window.voice_message)
        self.refresh_models()

    def refresh_models(self):
        settings = replace(self.manager.settings, models=self.paths.text().strip())
        available = installed_stt_models(settings)
        combo = self.choices["model"]
        for index in range(combo.count()):
            value = combo.itemData(index)
            title = {"whisper-small": "Small", "whisper-base": "Base", "whisper-tiny": "Tiny"}[value]
            combo.setItemText(index, title if value in available else title + " · niet geïnstalleerd")
            combo.model().item(index).setEnabled(value in available)
        if combo.currentData() not in available and available:
            combo.setCurrentIndex(combo.findData(next(name for name in ("whisper-small", "whisper-base", "whisper-tiny") if name in available)))
            if settings.models == self.manager.settings.models:
                replacement = replace(self.manager.settings, model=combo.currentData())
                try:
                    self.store.save(replacement)
                    self.manager.settings = replacement
                except OSError:
                    self.show_problem("Het beschikbare spraakmodel kon niet als voorkeur worden opgeslagen.")

    def show_problem(self, message):
        self.status.setText("Spraak lukt nog niet")
        self.error.setText(message)
        self.error.show()
        self.window.show_notice(message)

    def changed(self, state):
        if state != "Spraak lukt nog niet":
            self.error.hide()
        self.status.setText(state)
        self.window.stop_button.setEnabled(self.window.running or self.manager.responding)
        self.window.mic.setText("● Ik luister" if self.manager.recording else "Spraak / microfoon")
        self.ptt.setText("■  Opname afronden" if self.manager.recording else "●  Start luisteren")
        selected = self.inputs.currentText() if hasattr(self, "inputs") else "Windows-standaard"
        self.microphone_status.setText(("Microfoon actief · " if self.manager.recording else "Microfoon uit · ") + selected)
        if not self.manager.wake_enabled and self.wake.isChecked():
            self.wake.blockSignals(True)
            self.wake.setChecked(False)
            self.wake.blockSignals(False)

    def set_wake(self, enabled):
        self.manager.toggle_wake(enabled)
        self.wake.blockSignals(True)
        self.wake.setChecked(self.manager.wake_enabled)
        self.wake.blockSignals(False)

    def set_authorized(self, authorized):
        self.manager.set_authorized(authorized)
        central=bool(self.manager.options and self.manager.options["conversations"]["enabled"])
        if central:
            effective=self.manager.effective_settings()
            for key,field in self.fields.items():
                if key not in ("input_gain","followup_seconds"):field.setValue(getattr(effective,key))
            for key,field in self.choices.items():field.setCurrentIndex(field.findData(getattr(effective,key)))
            self.cache.setChecked(effective.cache)
        for key,field in self.fields.items():
            field.setEnabled(not central or key in ("input_gain","followup_seconds"))
            if central and key not in ("input_gain","followup_seconds"):field.setToolTip("Beheer deze voorkeur onder Instellingen → Gesprekken en geheugen.")
        for field in self.choices.values():
            field.setEnabled(not central)
            if central:field.setToolTip("De centrale server gebruikt de gedeelde stem- en modelvoorkeuren.")
        self.paths.setEnabled(not central)
        self.cache.setEnabled(not central)
        if not authorized:
            self.global_keys.setChecked(False)
            self.shortcuts.unregister()
            if not self.manager.responding:
                self.status.setText("Log in om te praten")

    def permission_changed(self, allowed):
        try:
            settings = replace(self.manager.settings, microphone_allowed=allowed)
            self.store.save(settings)
            self.manager.settings = settings
            self.manager.set_consent(allowed and self.manager.authorized)
        except (OSError, ValueError):
            self.consent.blockSignals(True)
            self.consent.setChecked(self.manager.settings.microphone_allowed)
            self.consent.blockSignals(False)
            self.window.show_notice("Microfoonvoorkeur kon niet worden opgeslagen.")

    def save_device(self, key, combo):
        try:
            self.window.voice_stop()
            settings = replace(self.manager.settings, **{key: combo.currentData()})
            self.store.save(settings)
            self.manager.settings = settings
            self.changed(self.manager.state)
        except (OSError, ValueError):
            self.window.show_notice("Audioapparaat kon niet worden opgeslagen.")

    def show_timings(self, values):
        parts = []
        for key, title in (("stt_seconds", "Spraak verstaan"), ("first_token_seconds", "Eerste antwoordtekst"), ("first_audio_seconds", "Eerste audio")):
            if key in values:
                parts.append(f"{title}: {values[key]:.1f} s")
        self.timings.setText(" · ".join(parts))

    def refresh_devices(self):
        def loaded(devices):
            if self.window.closing:
                return
            for combo, field, position in ((self.inputs, "input_device", 2), (self.outputs, "output_device", 3)):
                selected = getattr(self.manager.settings, field)
                combo.clear()
                combo.addItem("Windows-standaard", -1)
                for item in devices:
                    if item[position]:
                        combo.addItem(item[1], item[0])
                combo.setCurrentIndex(max(0, combo.findData(selected)))
        self.window.jobs.submit(lambda _: AudioDeviceManager().devices(), loaded, self.window.report_error)

    def save(self):
        try:
            self.window.voice_stop()
            settings = replace(self.manager.settings, **{key: field.value() for key, field in self.fields.items()},
                               **{key: field.currentData() for key, field in self.choices.items()},
                               models=self.paths.text().strip(), input_device=self.inputs.currentData(), output_device=self.outputs.currentData(),
                               cache=self.cache.isChecked(), ptt_shortcut=self.ptt_key.text().strip(), stop_shortcut=self.stop_key.text().strip(),
                               global_hotkeys=self.global_keys.isChecked())
            settings.validate()
            self.shortcuts.configure(settings, global_enabled=settings.global_hotkeys)
            self.store.save(settings)
            self.manager.settings = settings
            if settings.model not in installed_stt_models(settings):
                self.show_problem("Instellingen opgeslagen, maar het gekozen Whisper-model ontbreekt in deze map.")
            else:
                self.window.show_notice("Spraakinstellingen opgeslagen.")
        except (ValueError, OSError) as error:
            self.window.show_notice(str(error))

    def close_voice(self):
        self.shortcuts.close()
        self.manager.close()
