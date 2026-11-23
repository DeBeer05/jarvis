"""Native read-only views. All requests use the window's guarded worker bridge."""
import base64
from datetime import datetime
from urllib.parse import quote

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QLineEdit, QListWidget, QPlainTextEdit)

BASE = "/api/v1/automation"


def plain_label(text):
    value = QLabel(text)
    value.setTextFormat(Qt.TextFormat.PlainText)
    value.setWordWrap(True)
    return value


def mail_text(part):
    if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
        data = part["body"]["data"]
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")
    values = [mail_text(p) for p in part.get("parts", []) if p.get("mimeType") != "text/html"]
    if part.get("mimeType") == "multipart/alternative":
        return next((value for value in values if value), "")
    return "\n\n".join(value for value in values if value)


class IntegrationReads(QWidget):
    def __init__(self, window, kind):
        super().__init__(); self.window, self.kind = window, kind
        self.serial = 0; self.read_serial = 0; self.records = []; self.selected_mail = None
        self.allowed = False
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        self.status = plain_label("Haal gegevens op of vraag het via de Chat / Spraak.")
        layout.addWidget(self.status)
        controls = QHBoxLayout(); layout.addLayout(controls)
        if kind == "calendar":
            self.calendars = QComboBox(); self.calendars.addItem("Hoofdagenda", "primary")
            controls.addWidget(self.calendars, 1)
            self.load_calendars = QPushButton("Agenda’s ophalen"); controls.addWidget(self.load_calendars)
            self.load_calendars.clicked.connect(self.calendar_names)
            self.calendars.currentIndexChanged.connect(self.invalidate)
            dates = QHBoxLayout(); layout.addLayout(dates)
            self.start = QDateEdit(QDate.currentDate()); self.end = QDateEdit(QDate.currentDate().addDays(7))
            for title, field in (("Van", self.start), ("Tot (exclusief)", self.end)):
                field.setCalendarPopup(True); dates.addWidget(QLabel(title)); dates.addWidget(field)
                field.dateChanged.connect(self.invalidate)
            self.fetch = QPushButton("Afspraken ophalen"); dates.addWidget(self.fetch)
            self.fetch.clicked.connect(self.calendar)
            for title, days, span in (("Vandaag", 0, 1), ("Morgen", 1, 1), ("Komende week", 0, 7)):
                button = QPushButton(title); dates.addWidget(button)
                button.clicked.connect(lambda checked=False, d=days, s=span: self.period(d, s))
        else:
            self.query = QLineEdit(); self.query.setPlaceholderText("Zoek in Gmail, bijvoorbeeld in:inbox of from:naam")
            controls.addWidget(self.query, 1); self.query.textChanged.connect(self.invalidate)
            self.fetch = QPushButton("E-mails ophalen"); controls.addWidget(self.fetch)
            self.fetch.clicked.connect(self.mail_search); self.query.returnPressed.connect(self.mail_search)
        self.results = QListWidget(); layout.addWidget(self.results, 1)
        self.results.currentRowChanged.connect(self.select)
        self.reader = QPlainTextEdit(); self.reader.setReadOnly(True)
        self.reader.setPlaceholderText("Selecteer een afspraak of bericht.")
        layout.addWidget(self.reader, 1)
        if kind == "mail":
            self.open_body = QPushButton("Inhoud van geselecteerde e-mail lezen")
            self.open_body.clicked.connect(self.mail_body); layout.addWidget(self.open_body)

    def invalidate(self, *_):
        self.serial += 1; self.read_serial += 1
        self.records = []; self.selected_mail = None
        self.results.clear(); self.reader.clear()
        self.status.setText("Selectie gewijzigd. Haal de gegevens opnieuw op.")

    def clear(self):
        self.invalidate()
        if self.kind == "mail": self.query.clear()
        else:
            self.calendars.clear(); self.calendars.addItem("Hoofdagenda", "primary")
        self.status.setText("Nog geen gegevens opgehaald.")

    def set_authorized(self, allowed):
        if self.allowed and not allowed: self.clear()
        self.allowed = allowed; self.setEnabled(allowed)

    def request(self, method, path, body, done, *, token=None, selection=None):
        if not self.allowed: return
        token = self.serial if token is None else token
        def current(): return self.allowed and token == self.serial and (selection is None or selection == self.read_serial)
        def success(value):
            if current(): done(value)
        def failure(error):
            if current(): self.status.setText(str(error))
        self.window.call(method, BASE + path, body, success, failure)

    def calendar_names(self):
        self.invalidate(); self.status.setText("Agenda’s ophalen…")
        def loaded(data):
            selected = self.calendars.currentData()
            self.calendars.blockSignals(True); self.calendars.clear()
            for item in data.get("items", []):
                self.calendars.addItem(item.get("summaryOverride", item.get("summary", "Naamloze agenda")), item["id"])
            if self.calendars.count(): self.calendars.setCurrentIndex(max(0, self.calendars.findData(selected)))
            self.calendars.blockSignals(False)
            self.status.setText("Kies een agenda en haal de afspraken op." if self.calendars.count() else "Geen agenda’s gevonden.")
            if data.get("nextPageToken"): self.status.setText("De agendalijst is ingekort; niet alle agenda’s zijn getoond.")
        self.request("GET", "/calendar/calendars", None, loaded)

    def period(self, days, span):
        self.start.setDate(QDate.currentDate().addDays(days)); self.end.setDate(self.start.date().addDays(span))
        self.calendar()

    def calendar(self):
        if not self.calendars.currentData(): return
        self.invalidate()
        if self.end.date() <= self.start.date():
            self.status.setText("Kies een einddatum na de begindatum."); return
        # Aware local offsets follow the selected dates, including DST boundaries.
        def midnight(field): return datetime.combine(field.date().toPython(), datetime.min.time()).astimezone().isoformat()
        body = {"calendar_id": self.calendars.currentData(), "start": midnight(self.start), "end": midnight(self.end)}
        self.status.setText("Afspraken ophalen…")
        def loaded(data):
            self.records = data.get("items", [])[:100]
            for item in self.records:
                self.results.addItem(item.get("summary", "Zonder titel") + " — " + self.when(item.get("start", {})))
            self.status.setText(f"{len(self.records)} afspraken gevonden." if self.records else "Geen afspraken in deze agenda en periode.")
            if data.get("nextPageToken") or len(data.get("items", [])) > 100:
                self.status.setText("Eerste 100 afspraken. Kies een kortere periode voor een volledig overzicht.")
        self.request("POST", "/calendar/search", body, loaded)

    @staticmethod
    def when(value):
        if value.get("dateTime"):
            try: return datetime.fromisoformat(value["dateTime"]).astimezone().strftime("%d-%m-%Y %H:%M")
            except ValueError: return "Onbekend tijdstip"
        return value.get("date", "Onbekend tijdstip") + " (hele dag)"

    def mail_search(self):
        self.invalidate(); token = self.serial
        self.status.setText("E-mails zoeken…")
        def found(data):
            ids = [item["id"] for item in data.get("messages", [])[:5]]
            def next_message(index):
                if token != self.serial: return
                if index == len(ids):
                    self.status.setText(f"{len(self.records)} berichten: alleen afzender en onderwerp." if ids else "Geen e-mails gevonden.")
                    if data.get("nextPageToken") or len(data.get("messages", [])) > 5:
                        self.status.setText("Eerste vijf berichten: alleen afzender en onderwerp. Verfijn je zoekopdracht voor meer.")
                    return
                def metadata(mail):
                    headers = {h["name"].lower(): h["value"] for h in mail.get("payload", {}).get("headers", [])}
                    record = {"id": mail["id"], "subject": headers.get("subject", "Zonder onderwerp"), "from": headers.get("from", "Onbekende afzender")}
                    self.records.append(record); self.results.addItem(record["subject"] + " — " + record["from"])
                    next_message(index + 1)
                self.request("GET", "/email/" + quote(ids[index], safe=""), None, metadata, token=token)
            next_message(0)
        self.request("POST", "/email/search", {"query": self.query.text().strip() or "in:inbox"}, found, token=token)

    def select(self, index):
        self.read_serial += 1; self.selected_mail = None; self.reader.clear()
        if not 0 <= index < len(self.records): return
        item = self.records[index]
        if self.kind == "calendar":
            text = item.get("summary", "Zonder titel") + "\nVan: " + self.when(item.get("start", {})) + "\nTot: " + self.when(item.get("end", {}))
            if item.get("location"): text += "\nLocatie: " + item["location"]
            self.reader.setPlainText(text)
        else:
            self.selected_mail = item["id"]
            self.reader.setPlainText("Van: " + item["from"] + "\nOnderwerp: " + item["subject"] + "\n\nKlik op Inhoud lezen om de berichttekst op te halen.")

    def mail_body(self):
        if not self.selected_mail:
            self.status.setText("Selecteer eerst een bericht uit de lijst."); return
        self.read_serial += 1; selection = self.read_serial; identifier = self.selected_mail
        self.status.setText("Geselecteerde e-mail lezen…")
        def loaded(mail):
            if selection != self.read_serial or identifier != self.selected_mail: return
            headers = {h["name"].lower(): h["value"] for h in mail.get("payload", {}).get("headers", [])}
            try: text = mail_text(mail.get("payload", {}))
            except (ValueError, TypeError): text = "De tekst kon niet worden gedecodeerd."
            if not text: text = "Geen gewone tekstversie beschikbaar. Korte weergave:\n" + mail.get("snippet", "")
            self.reader.setPlainText("Van: " + headers.get("from", "Onbekend") + "\nOnderwerp: " + headers.get("subject", "Zonder onderwerp") + "\n\n" + text[:20000])
            self.status.setText("Berichtinhoud gelezen. HTML en externe afbeeldingen worden niet geladen." + (" Bericht ingekort." if len(text) > 20000 else ""))
        self.request("GET", "/email/" + quote(identifier, safe="") + "?include_body=true", None, loaded, selection=selection)
