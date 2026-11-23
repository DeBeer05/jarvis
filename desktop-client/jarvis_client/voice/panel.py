from dataclasses import replace
import json

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                              QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from jarvis_client.voice.audio import AudioDeviceManager
from jarvis_client.voice.manager import VoiceConversationManager
from jarvis_client.voice.settings import VoiceSettingsManager, model_directory
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
        self.status = QLabel("Microfoon uit")
        self.status.setObjectName("notice")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.consent = QCheckBox("Ik geef deze appsessie toestemming om mijn microfoon te gebruiken")
        self.consent.toggled.connect(self.manager.set_consent)
        layout.addWidget(self.consent)
        controls = QHBoxLayout()
        self.ptt = QPushButton("●  Spreken / opname verwerken")
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
        self.wake = QCheckBox("Hé JARVIS · lokale fraseherkenning (experimenteel)")
        self.wake.toggled.connect(self.set_wake)
        layout.addWidget(self.wake)
        note = QLabel("Luistert alleen met jouw toestemming. Wake word wordt na een hele uiting herkend; geen getraind Nederlands wake-wordmodel. Tijdens spreken staat de microfoon uit.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.transcript, self.answer = QPlainTextEdit(), QPlainTextEdit()
        for box, placeholder in ((self.transcript, "Herkende Nederlandse spraak verschijnt hier na de opname."), (self.answer, "Het antwoord verschijnt hier tijdens het streamen.")):
            box.setReadOnly(True)
            box.setPlaceholderText(placeholder)
            box.setMaximumHeight(90)
            layout.addWidget(box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
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
        layout.addWidget(self.timings)
        self.manager.changed.connect(self.changed)
        self.manager.problem.connect(window.show_notice)
        self.manager.transcript.connect(self.transcript.setPlainText)
        self.manager.answer.connect(self.answer.setPlainText)
        self.manager.metrics.connect(lambda values: self.timings.setText("Lokale meting: " + json.dumps(values, ensure_ascii=False)))
        self.manager.ready_text.connect(window.voice_message)

    def changed(self, state):
        self.status.setText(state)
        self.window.stop_button.setEnabled(self.window.running or self.manager.responding)
        self.window.mic.setText("● Microfoon actief" if self.manager.recording else "Spraak / microfoon")
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
        self.consent.setEnabled(authorized)
        if not authorized:
            self.consent.setChecked(False)
            self.global_keys.setChecked(False)
            self.shortcuts.unregister()

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
            self.window.show_notice("Spraakinstellingen opgeslagen. Er is geen modeldownload of opname gestart.")
        except (ValueError, OSError) as error:
            self.window.show_notice(str(error))

    def close_voice(self):
        self.shortcuts.close()
        self.manager.close()
