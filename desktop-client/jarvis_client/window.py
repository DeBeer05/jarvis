import json
import time
from uuid import uuid4

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QTextCursor
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout, QFrame, QHBoxLayout,
                              QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
                              QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget, QTabWidget,
                              QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget)

from jarvis_client import __version__
from jarvis_client.api import ClientError
from jarvis_client.connection import ConnectionManager, Jobs
from jarvis_client.platform_services import LocalAgent, NotificationCenter, Startup
from jarvis_client.voice.panel import VoicePanel
from jarvis_client.settings import Preferences
from jarvis_client.theme import icon, stylesheet
from jarvis_client.automations import AutomationPanel
from jarvis_client.natural_settings import NaturalSettingsPanel
from jarvis_client.voice.session import ConversationSession
from jarvis_client.voice.server_worker import ServerInferenceWorker
from jarvis_client.voice.worker import InferenceWorker


def label(text, name=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    if primary:
        widget.setObjectName("primary")
    widget.clicked.connect(callback)
    return widget


class Composer(QPlainTextEdit):
    send = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.send.emit()
        else:
            super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, store, vault, *, preferences=None, manager_factory=ConnectionManager):
        super().__init__()
        self.store, self.preferences = store, preferences or store.load()
        self.jobs = Jobs(self)
        self.manager = manager_factory(self.preferences, vault, self.jobs, self)
        self.principal = None
        self.conversation = None
        self.history_offset = 0
        self.request_id = None
        self.running = False
        self.history_busy = False
        self.closing = False
        self.previous_state = "offline"
        self.reply = ""
        self.rows = []
        self.login_busy = False
        self.active_origin = None
        self.permissions = LocalAgent()
        self.pending_voice = None
        self.natural_refresh=0
        self.setWindowTitle("JARVIS — Desktop")
        self.setWindowIcon(icon())
        self.resize(1160, 790)
        self.setMinimumSize(760, 580)
        self.setStyleSheet(stylesheet(self.preferences.theme))
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(202)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(16, 22, 16, 18)
        side.addWidget(label("J A R V I S", "brand"))
        side.addWidget(label("JOUW DENKRUIMTE", "eyebrow"))
        side.addSpacing(28)
        self.pages = QStackedWidget()
        self.nav = []
        for index, title in enumerate(("Chat", "Gesprekken", "Apparaten", "Meldingen", "Instellingen", "Account", "Spraak", "Automatiseringen")):
            nav = button(title, lambda checked=False, i=index: self.navigate(i))
            nav.setObjectName("nav")
            nav.setCheckable(True)
            self.nav.append(nav)
            side.addWidget(nav)
        side.addStretch()
        self.connection_label = label("○  Verbinding controleren", "muted")
        side.addWidget(self.connection_label)
        side.addWidget(label("Desktop  " + __version__, "muted"))
        side.addWidget(button("App afsluiten", self.shutdown))
        layout.addWidget(self.sidebar)
        content = QVBoxLayout()
        content.addWidget(self.pages)
        self.notice = label("", "notice")
        self.notice.hide()
        content.addWidget(self.notice)
        layout.addLayout(content, 1)
        self.make_chat()
        self.make_history()
        self.make_devices()
        self.make_notifications()
        self.make_settings()
        self.make_account()
        self.voice_panel = VoicePanel(self)
        self.voice = self.voice_panel.manager
        self.voice_session=ConversationSession(self)
        self.voice.session_ended.connect(self.voice_session.end)
        self.voice.playback_finished.connect(self.voice_session.listened)
        self.voice.interrupted.connect(lambda:self.stop_answer(stop_voice=False))
        self.voice.metrics.connect(self.voice_metrics)
        self.pages.addWidget(self.voice_panel)
        self.automation_panel = AutomationPanel(self)
        self.pages.addWidget(self.automation_panel)
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self.render)
        self.setup_tray()
        self.notifications = NotificationCenter(self.deliver_notification)
        self.notifications.enabled = self.preferences.notifications
        self.notifications.answers = self.preferences.notify_answers
        self.manager.changed.connect(self.connection_changed)
        self.manager.authenticated.connect(self.authenticated)
        self.manager.problem.connect(self.report_error)
        self.navigate(0)
        self.update_controls()
        if self.preferences.auto_connect:
            QTimer.singleShot(0, self.manager.start)

    def page(self, title, description):
        widget = QWidget()
        body = QVBoxLayout(widget)
        body.setContentsMargins(8, 10, 8, 0)
        body.setSpacing(14)
        body.addWidget(label(title, "heading"))
        body.addWidget(label(description, "muted"))
        self.pages.addWidget(widget)
        return body

    def make_chat(self):
        body = self.page("Een nieuw perspectief begint hier.", "Stel een vraag, werk een idee uit of ga verder waar je was gebleven.")
        bar = QHBoxLayout()
        self.provider = QComboBox()
        for title, value in (("Automatisch", "auto"), ("Groq", "groq"), ("Gemini", "gemini"), ("Ollama · lokaal", "ollama")):
            self.provider.addItem(title, value)
        self.provider.setCurrentIndex(max(0, self.provider.findData(self.preferences.provider)))
        self.model_info = label("Provider en model verschijnen na verbinding.", "muted")
        bar.addWidget(self.model_info, 1)
        bar.addWidget(self.provider)
        self.new_button = button("＋ Nieuw gesprek", self.new_conversation)
        bar.addWidget(self.new_button)
        body.addLayout(bar)
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setAcceptRichText(False)
        self.transcript.setPlaceholderText("JARVIS\n\nJouw werkruimte staat klaar. Log in met je gebruikersnaam en wachtwoord om te beginnen.")
        body.addWidget(self.transcript, 1)
        self.composer = Composer()
        self.composer.setPlaceholderText("Typ je bericht…  Enter verstuurt · Shift+Enter nieuwe regel")
        self.composer.setMaximumHeight(105)
        self.composer.send.connect(self.send_message)
        body.addWidget(self.composer)
        actions = QHBoxLayout()
        self.mic = button("Spraak / microfoon", lambda: self.navigate(6))
        self.mic.setToolTip("Open het spraakpaneel; de microfoon vereist jouw toestemming")
        actions.addWidget(self.mic)
        actions.addWidget(button('Uitjesplanning',self.show_planning))
        actions.addStretch()
        self.stop_button = button("Stop antwoord", self.stop_answer)
        self.send_button = button("Versturen  →", self.send_message, True)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.send_button)
        body.addLayout(actions)

    def make_history(self):
        body = self.page("Gesprekken", "Je geschiedenis blijft op de server. Alleen expliciet gekozen gesprekken worden verwijderd.")
        self.history = QListWidget()
        self.history.itemDoubleClicked.connect(self.open_conversation)
        body.addWidget(self.history, 1)
        bar = QHBoxLayout()
        bar.addWidget(button("Vernieuwen", lambda: self.load_history()))
        self.more_history = button("Meer laden", lambda: self.load_history(True))
        bar.addWidget(self.more_history)
        bar.addWidget(button("Gesprek openen", self.open_conversation))
        self.delete_button = button("Gesprek verwijderen", self.delete_conversation)
        bar.addWidget(self.delete_button)
        body.addLayout(bar)

    def make_devices(self):
        body = self.page("Apparaten", "Deze app heeft een eigen intrekbare Windows-identiteit. Beheer andere apparaten als eigenaar in je browser.")
        self.device_info = label("Nog geen gekoppeld apparaat.")
        body.addWidget(self.device_info)
        body.addWidget(button("Apparaatstatus vernieuwen", self.load_device))
        body.addWidget(button("Eigenaarinterface openen", self.open_security))
        self.revoke_button = button("Deze apparaatkoppeling intrekken", self.revoke_device)
        body.addWidget(self.revoke_button)
        body.addStretch()

    def make_notifications(self):
        body = self.page("Meldingen", "Verbinding en belangrijke status, zonder chatinhoud op je vergrendelscherm.")
        self.notification_list = QListWidget()
        body.addWidget(self.notification_list, 1)
        body.addWidget(button("Testmelding tonen", lambda: self.notify("test", "Dit is een lokale JARVIS-testmelding.")))
        body.addWidget(label("Je agenda, e-mail en herinneringen staan onder Automatiseringen. Je kunt ze ook via Chat of Spraak opvragen.", "muted"))

    def make_settings(self):
        body = self.page("Instellingen", "Vertrouwde endpoints, rustig gedrag en voorkeuren voor deze Windows-app.")
        tabs=QTabWidget();body.addWidget(tabs,1)
        local=QWidget();tabs.addTab(local,"Deze Windows-app");body=QVBoxLayout(local)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setSpacing(12)
        self.local_url = QLineEdit(self.preferences.local_url)
        self.remote_url = QLineEdit(self.preferences.remote_url)
        self.remote_url.setPlaceholderText("https:// — optioneel, later activeren")
        self.mode = QComboBox()
        for title, value in (("Alleen lokaal", "local"), ("Alleen extern HTTPS", "remote"), ("Lokaal, anders expliciet extern profiel", "auto")):
            self.mode.addItem(title, value)
        self.mode.setCurrentIndex(self.mode.findData(self.preferences.connection_mode))
        form.addRow("Lokale server", self.local_url)
        form.addRow("Externe HTTPS-server", self.remote_url)
        form.addRow("Profiel", self.mode)
        self.setting_checks = {}
        for key, title in (("auto_connect", "Automatisch verbinden"), ("minimize_to_tray", "Venster sluiten naar systeemvak"),
                           ("notifications", "Windows-meldingen"), ("notify_answers", "Melding als een antwoord klaar is"), ("startup", "Start deze app bij Windows-aanmelding")):
            check = QCheckBox(title)
            check.setChecked(getattr(self.preferences, key))
            self.setting_checks[key] = check
            form.addRow(check)
        self.theme_choice, self.language_choice, self.log_choice = QComboBox(), QComboBox(), QComboBox()
        for title, value in (("Donker", "dark"), ("Licht", "light")):
            self.theme_choice.addItem(title, value)
        self.theme_choice.setCurrentIndex(self.theme_choice.findData(self.preferences.theme))
        for title, value in (("Nederlands", "nl"), ("English", "en")):
            self.language_choice.addItem(title, value)
        self.language_choice.setCurrentIndex(self.language_choice.findData(self.preferences.language))
        for value in ("warning", "info", "debug"):
            self.log_choice.addItem(value)
        self.log_choice.setCurrentText(self.preferences.log_level)
        form.addRow("Thema", self.theme_choice)
        form.addRow("Taal", self.language_choice)
        form.addRow("Logniveau", self.log_choice)
        scroll.setWidget(inner)
        body.addWidget(scroll, 1)
        body.addWidget(button("Instellingen opslaan", self.save_settings, True))
        body.addWidget(button("Nu verbinding controleren", self.manager.start))
        self.diagnostics = label("TLS-validatie altijd actief · HTTP alleen loopback · geen proxyheaders of serverstart", "muted")
        body.addWidget(self.diagnostics)
        permissions = QHBoxLayout()
        self.local_permission = QCheckBox("Ik geef toestemming om lokale systeeminformatie te lezen")
        permissions.addWidget(self.local_permission, 1)
        permissions.addWidget(button("Systeeminformatie", self.system_info))
        body.addLayout(permissions)
        self.natural_settings=NaturalSettingsPanel(self)
        tabs.addTab(self.natural_settings,"Gesprekken en geheugen")
        self.natural_settings.tabs.currentChanged.connect(lambda index:self.natural_settings.load_memory() if index==1 and self.principal else None)
        self.natural_settings.tabs.currentChanged.connect(lambda index:self.natural_settings.refresh_diagnostics() if index==2 and self.principal else None)

    def make_account(self):
        body = self.page("Account", "Log in met je bestaande JARVIS-gebruikersnaam en wachtwoord. Je blijft na het afsluiten van de app ingelogd.")
        self.account_info = label("Niet ingelogd.")
        body.addWidget(self.account_info)
        self.login_form = QWidget()
        form = QFormLayout(self.login_form)
        form.setContentsMargins(0, 0, 0, 0)
        self.username = QLineEdit()
        self.username.setPlaceholderText("Je JARVIS-gebruikersnaam")
        self.username.setMaxLength(64)
        self.username.setAccessibleName("Gebruikersnaam")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMaxLength(128)
        self.password.setAccessibleName("Wachtwoord")
        self.password.returnPressed.connect(self.login)
        form.addRow("Gebruikersnaam", self.username)
        form.addRow("Wachtwoord", self.password)
        self.device_name = QLineEdit("JARVIS Windows")
        self.device_name.setMaxLength(80)
        self.device_name.setPlaceholderText("Naam voor dit apparaat")
        form.addRow("Apparaatnaam", self.device_name)
        body.addWidget(self.login_form)
        self.login_button = button("Inloggen", self.login, True)
        body.addWidget(self.login_button)
        body.addWidget(label("Je wachtwoord wordt niet bewaard. Windows Credential Manager bewaart uitsluitend je beveiligde sessie.", "muted"))
        body.addWidget(button("Wachtwoord en eigenaarsessies beheren", self.open_security))
        self.logout_button = button("Uitloggen op deze app", self.logout)
        body.addWidget(self.logout_button)
        body.addStretch()
        body.addWidget(label("Refresh-token: Windows Credential Manager. Geen wachtwoorden of tokens in je instellingen.", "muted"))

    def setup_tray(self):
        self.tray = QSystemTrayIcon(icon(), self)
        self.tray.setToolTip("JARVIS · niet verbonden")
        menu = QMenu(self)
        for title, callback in (("JARVIS openen", self.restore), ("Meldingen", lambda: self.restore_page(3)), ("Instellingen", lambda: self.restore_page(4)), ("Volledig afsluiten", self.shutdown)):
            action = QAction(title, menu)
            action.triggered.connect(callback)
            menu.addAction(action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.restore() if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick) else None)
        self.tray.messageClicked.connect(lambda: self.restore_page(3))
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        for i, nav in enumerate(self.nav):
            nav.setChecked(i == index)
        if index == 1:
            self.load_history()
        elif index == 2:
            self.load_device()
        elif index == 7:
            self.automation_panel.refresh()
        elif index == 4 and self.natural_settings.document is None:
            self.natural_settings.refresh()

    def show_notice(self, text):
        self.notice.setText(text)
        self.notice.setVisible(bool(text))

    def report_error(self, error):
        self.show_notice(str(error))
        if isinstance(error, ClientError) and error.status == 401:
            self.clear_private()
            self.manager.state = "login"
            self.update_controls()

    def connection_changed(self, state):
        titles = {"online": "●  Verbonden", "login": "○  Inloggen nodig", "offline": "○  Niet bereikbaar"}
        self.connection_label.setText(titles[state])
        self.tray.setToolTip("JARVIS · " + titles[state])
        if self.previous_state == "online" and state == "offline":
            self.notify("lost", "Verbinding verloren. JARVIS probeert automatisch opnieuw.")
        if state == "online" and self.previous_state == "offline":
            self.notify("restored", "Verbinding met JARVIS hersteld.")
        if state == "login":
            self.clear_private()
            self.account_info.setText("Niet ingelogd. Vul je gebruikersnaam en wachtwoord in.")
            if self.previous_state != "login":
                self.show_notice("Server bereikbaar. Log in met je gebruikersnaam en wachtwoord.")
                self.navigate(5)
        self.previous_state = state
        self.diagnostics.setText(f"Profiel: {self.preferences.connection_mode} · {self.manager.api.origin if self.manager.api else 'geen server'}\nTLS-validatie actief; geen automatische publieke toegang.")
        self.update_controls()

    def authenticated(self, principal):
        if self.active_origin != self.manager.api.origin:
            self.clear_private()
            self.active_origin = self.manager.api.origin
        first = not self.principal or principal["session_id"] != self.principal["session_id"]
        self.principal = principal
        self.account_info.setText("Ingelogd · Windows-apparaat " + principal["device_id"] + "\nRechten: " + ", ".join(principal["permissions"]))
        self.update_controls()
        if first or time.monotonic()-self.natural_refresh>30:
            self.natural_refresh=time.monotonic()
            self.call("GET","/api/v1/natural/settings",None,self.apply_natural_settings)
        if first:
            self.show_notice("Verbonden. Je gesprekken staan klaar.")
            self.load_history()
            self.load_device()
            if "status:read" in principal["permissions"]:
                self.call("GET", "/api/v1/ai/providers", None, self.providers_loaded)

    def providers_loaded(self, result):
        self.model_info.setText(" · ".join(f"{name}: {value.get('model', '—')}" for name, value in result.get("providers", {}).items()))

    def apply_natural_settings(self,document):
        self.voice.configure_natural(document["settings"])
        enabled=document["settings"]["conversations"]["enabled"]
        worker=self.voice.next_worker or self.voice.worker
        if enabled and self.manager.api and (not isinstance(worker,ServerInferenceWorker) or worker.api is not self.manager.api):
            self.voice.select_worker(ServerInferenceWorker(self.manager.api))
        elif not enabled and isinstance(worker,ServerInferenceWorker):
            self.voice.select_worker(InferenceWorker())
        self.voice_panel.set_authorized(bool(self.principal and "chat:write" in self.principal["permissions"] and self.manager.state=="online"))

    def update_controls(self):
        permissions = set(self.principal["permissions"]) if self.principal else set()
        self.automation_panel.set_authorized(permissions,self.manager.state=="online")
        self.voice_panel.set_authorized("chat:write" in permissions and self.manager.state == "online")
        self.send_button.setEnabled("chat:write" in permissions and not self.running and self.manager.state == "online")
        self.stop_button.setEnabled(self.running or self.voice.responding)
        self.new_button.setEnabled(not self.running)
        self.delete_button.setEnabled("chat:delete" in permissions and not self.running)
        self.logout_button.setEnabled(bool(self.principal) and not self.running)
        self.revoke_button.setEnabled(bool(self.principal) and not self.running)
        self.login_button.setEnabled(self.manager.state == "login" and not self.login_busy)
        self.login_button.setVisible(not bool(self.principal))
        self.login_form.setVisible(not bool(self.principal))
        self.login_form.setEnabled(not self.login_busy)
        self.provider.setEnabled(not self.running)

    def call(self, method, path, body, success, failure=None):
        api = self.manager.api
        if not api or not self.principal:
            self.show_notice("Log eerst in met je gebruikersnaam en wachtwoord.")
            return
        generation = self.manager.generation
        def done(value):
            if generation == self.manager.generation and self.principal and not self.closing:
                success(value)
        def failed(error):
            if generation == self.manager.generation and self.principal and not self.closing:
                if failure: failure(error)
                self.report_error(error)
        self.jobs.submit(lambda _: api.request(method, path, body), done, failed)

    def login(self):
        api = self.manager.api
        if self.login_busy or self.principal:
            return
        if not api or self.manager.state != "login":
            self.manager.start()
            self.show_notice("Wacht op de serververbinding en probeer daarna opnieuw.")
            return
        username, password = self.username.text().strip(), self.password.text()
        name = self.device_name.text().strip()
        if not username or not password or not name:
            self.show_notice("Vul je gebruikersnaam, wachtwoord en apparaatnaam in.")
            return
        self.password.clear()
        try:
            # Persist only this installation's public UUID and non-secret settings.
            self.store.save(self.preferences)
        except (ValueError, OSError):
            self.show_notice("Instellingen konden niet worden opgeslagen. Je wachtwoord is niet bewaard.")
            return
        self.login_busy = True
        self.manager.login_pending = True
        self.manager.generation += 1
        self.manager.timer.stop()
        generation = self.manager.generation
        installation_id = self.preferences.installation_id
        self.update_controls()
        def done(result):
            self.login_busy = False
            self.manager.login_pending = False
            if api is not self.manager.api or generation != self.manager.generation or self.closing:
                return
            self.manager.state = "online"
            self.connection_changed("online")
            self.authenticated(result)
            self.navigate(0)
            self.manager.timer.start(20000)
        def failed(error):
            self.login_busy = False
            self.manager.login_pending = False
            if generation == self.manager.generation and not self.closing:
                self.report_error(error)
                self.update_controls()
                self.manager.timer.start(20000)
        self.jobs.submit(lambda _: api.login(username, password, name, installation_id), done, failed)

    def open_security(self):
        origin = self.manager.api.origin if self.manager.api else self.preferences.candidates()[0]
        QDesktopServices.openUrl(QUrl(origin + "/security"))

    def load_history(self, append=False):
        if not self.principal or "chat:read" not in self.principal["permissions"] or self.history_busy:
            return
        if not append:
            self.history_offset = 0
            self.history.clear()
        self.history_busy = True
        offset = self.history_offset
        generation = self.manager.generation
        def loaded(result):
            if generation != self.manager.generation or not self.principal or self.closing:
                return
            self.history_busy = False
            for item in result["items"]:
                row = QListWidgetItem(item["title"])
                row.setData(Qt.ItemDataRole.UserRole, item["id"])
                self.history.addItem(row)
            self.history_offset += len(result["items"])
            self.more_history.setEnabled(result.get("has_more", False))
        api = self.manager.api
        def failed(error):
            if generation != self.manager.generation or not self.principal or self.closing:
                return
            self.history_busy = False
            self.report_error(error)
        self.jobs.submit(lambda _: api.request("GET", f"/api/v1/chat/conversations?limit=50&offset={offset}"), loaded, failed)

    def open_conversation(self, item=None):
        if self.running:
            self.show_notice("Stop eerst het lopende antwoord.")
            return
        row = item if isinstance(item, QListWidgetItem) else self.history.currentItem()
        if not row:
            return
        identifier = row.data(Qt.ItemDataRole.UserRole)
        def loaded(result):
            self.voice.stop()
            self.voice_session.end()
            self.conversation = identifier
            if hasattr(self,'planning_panel'):
                self.planning_panel.overview.clear();self.planning_panel.edit.clear()
                if self.planning_panel.isVisible():self.planning_panel.refresh()
            self.rows = []
            for turn in result["turns"]:
                self.rows += [("JIJ", turn["user_text"]), ("JARVIS", turn["assistant_text"] + ("\n[" + turn["status"] + "]" if turn["status"] != "completed" else ""))]
            self.render()
            self.navigate(0)
        self.call("GET", "/api/v1/chat/conversations/" + identifier, None, loaded)

    def delete_conversation(self):
        row = self.history.currentItem()
        if not row or self.running:
            return
        if QMessageBox.question(self, "Gesprek verwijderen", "Dit gesprek met alle berichten definitief verwijderen?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        identifier = row.data(Qt.ItemDataRole.UserRole)
        def deleted(_):
            if self.conversation == identifier:
                self.new_conversation()
            self.load_history()
        self.call("DELETE", "/api/v1/chat/conversations/" + identifier, None, deleted)

    def new_conversation(self):
        if self.running:
            return
        self.voice.stop()
        self.voice_session.end()
        self.conversation = None
        if hasattr(self,'planning_panel'):
            self.planning_panel.overview.clear();self.planning_panel.edit.clear();self.planning_panel.hide()
        self.rows = []
        self.transcript.clear()
        self.navigate(0)

    def render(self):
        bar = self.transcript.verticalScrollBar()
        bottom = bar.value() >= bar.maximum() - 30
        self.transcript.setPlainText("\n\n".join(name + "\n" + text for name, text in self.rows))
        if bottom or self.running:
            self.transcript.moveCursor(QTextCursor.MoveOperation.End)

    def show_planning(self):
        from jarvis_client.planning_panel import PlanningPanel
        if not hasattr(self,'planning_panel'):self.planning_panel=PlanningPanel(self)
        self.planning_panel.show();self.planning_panel.raise_();self.planning_panel.refresh()

    def send_message(self):
        if not self.send_button.isEnabled() or self.running:
            return
        message = self.composer.toPlainText().strip()
        if not message or len(message) > 8000:
            self.show_notice("Typ een bericht van maximaal 8000 tekens.")
            return
        api = self.manager.api
        channel="voice" if self.voice.voice_next else "text"
        epoch=self.voice_session.current["epoch"] if channel=="voice" and self.voice_session.current else None
        self.voice.begin_response()
        self.request_id = str(uuid4())
        request_id, conversation, provider = self.request_id, self.conversation, self.provider.currentData()
        self.reply = ""
        self.rows += [("JIJ", message), ("JARVIS", "…")]
        self.composer.clear()
        self.running = True
        self.manager.pinned = True
        self.update_controls()
        self.render()
        self.show_notice("")
        generation = self.manager.generation
        def current():
            return not self.closing and generation == self.manager.generation and self.request_id == request_id and bool(self.principal)
        def finished(_):
            if not current():
                return
            self.running = False
            self.manager.pinned = False
            self.update_controls()
            self.load_history()
            if self.pending_voice:
                pending, self.pending_voice = self.pending_voice, None
                self.voice.voice_next = True
                self.voice_message(pending)
        def failed(error):
            if not current():
                return
            self.voice.finish_response(False)
            self.pending_voice = None
            self.running = False
            self.manager.pinned = False
            if self.rows:
                self.rows[-1] = ("JARVIS", self.reply + "\n[Antwoord niet voltooid]")
                self.render()
            self.report_error(error)
            self.update_controls()
        self.jobs.submit(lambda emit: api.stream(message, conversation, provider, emit, request_id,**({"channel":channel,"session_epoch":epoch} if channel=="voice" else {})), finished, failed,
                         lambda event: self.stream_event(event) if current() else None)

    def voice_ptt(self):
        if self.running and not self.voice.recording:
            self.stop_answer()
        if not self.voice.recording and self.voice_session.enabled() and self.principal and self.voice.consent:
            self.voice_session.prepare_capture(self.voice.toggle_recording)
            return
        self.voice.toggle_recording()

    def voice_metrics(self,measurements):
        if not self.principal or self.manager.state!="online":return
        items=[]
        for key,event in (("first_audio_seconds","native_first_audio_ms"),("stt_seconds","native_stt_ms"),("total_seconds","native_total_ms")):
            if key in measurements:items.append({"event":event,"value":float(measurements[key])*1000})
        for event in ("interruption","rejected_interruption","wake_miss"):
            if event in measurements:items.append({"event":event,"value":float(measurements[event])})
        if items:self.call("POST","/api/v1/natural/diagnostics/metrics",{"items":items},lambda _:None,lambda _:None)

    def voice_stop(self):
        self.pending_voice = None
        self.voice.stop()
        self.stop_answer()
        self.voice_session.end()

    def voice_message(self, text):
        if not self.principal or self.manager.state != "online":
            self.voice.stop()
            self.show_notice("Log opnieuw in voordat je een spraakopdracht verstuurt.")
            return
        if self.running:
            self.pending_voice = text
            self.stop_answer(stop_voice=False)
            return
        if self.voice_session.enabled():
            self.voice_session.submit(text)
            return
        self.send_voice_text(text)

    def send_voice_text(self,text):
        self.composer.setPlainText(text)
        self.send_message()

    def stream_event(self, event):
        if self.closing or not self.running:
            return
        kind = event["type"]
        if kind == "meta":
            self.server_speech=bool(event.get("speech_protocol"))
            self.conversation = event["conversation_id"]
            if hasattr(self.voice.worker,"begin_utterance"):self.voice.worker.begin_utterance(event["request_id"],self.conversation)
        elif kind == "provider":
            self.model_info.setText(str(event["provider"]) + " · " + str(event["model"]))
        elif kind == 'planning':
            if hasattr(self,'planning_panel'):self.planning_panel.show_plan(event['planning'])
        elif kind == "delta":
            if not getattr(self,"server_speech",False):self.voice.delta(event["text"])
            self.reply += event["text"]
            if getattr(self,"server_speech",False):self.voice_panel.answer.setPlainText(self.reply)
            self.rows[-1] = ("JARVIS", self.reply)
            if not self.render_timer.isActive():
                self.render_timer.start(40)
        elif kind == "speech":
            if getattr(self,"server_speech",False):
                self.voice.delta(event["text"],ready=True)
                # Echo suppression tracks spoken text; the panel shows all text.
                if self.reply:self.voice_panel.answer.setPlainText(self.reply)
        elif kind == "fallback":
            self.show_notice("Provider niet beschikbaar. JARVIS schakelt over naar " + event["to"] + ".")
        elif kind == "error":
            self.voice.finish_response(False)
            self.show_notice(event["message"])
        elif kind == "done":
            self.voice.finish_response(event["status"] == "completed")
            self.render_timer.stop()
            self.reply = event["message"]
            if getattr(self,"server_speech",False):self.voice_panel.answer.setPlainText(self.reply)
            self.rows[-1] = ("JARVIS", self.reply + ("\n[" + event["status"] + "]" if event["status"] != "completed" else ""))
            self.render()
            if event["status"] == "completed" and not self.isActiveWindow():
                self.notify("answer", "Je JARVIS-antwoord staat klaar.")

    def stop_answer(self,*,stop_voice=True):
        if stop_voice:self.voice.stop()
        if not self.running or not self.manager.api:
            return
        self.call("POST", "/api/v1/chat/requests/" + self.request_id + "/cancel", None, lambda _: self.show_notice("Antwoord wordt gestopt."))

    def load_device(self):
        if not self.principal:
            return
        def loaded(item):
            self.device_info.setText(f"{item['name']}\n{item['type']} · {'Vertrouwd' if item['trusted'] else 'Ingetrokken'}\n{item['id']}\n\nRechten: " + ", ".join(item["permissions"]))
        self.call("GET", "/api/v1/auth/device", None, loaded)

    def logout(self, checked=False, revoke=False):
        api = self.manager.api
        if not api:
            return
        self.jobs.submit(lambda _: api.logout(revoke), lambda _: self.logged_out(), lambda error: (self.logged_out(), self.show_notice("Lokaal uitgelogd. Als de server onbereikbaar was: trek deze sessie ook in via de eigenaarinterface.")))

    def logged_out(self):
        if hasattr(self,'planning_panel'):
            self.planning_panel.overview.clear();self.planning_panel.edit.clear();self.planning_panel.hide()
        self.clear_private()
        self.manager.reset()
        self.navigate(5)
        self.show_notice("Uitgelogd op deze Windows-app.")

    def revoke_device(self):
        if QMessageBox.question(self, "Apparaat intrekken", "Alle toegang van deze Windows-app intrekken? Opnieuw inloggen is daarna nodig.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.logout(revoke=True)

    def clear_private(self):
        if hasattr(self,"voice_session"):self.voice_session.clear()
        if hasattr(self,"automation_panel"): self.automation_panel.clear()
        if hasattr(self,"natural_settings"):self.natural_settings.clear()
        self.pending_voice = None
        self.voice_panel.set_authorized(False)
        self.render_timer.stop()
        self.history_busy = False
        self.principal = None
        self.conversation = None
        self.rows = []
        self.running = False
        self.manager.pinned = False
        self.transcript.clear()
        self.history.clear()
        self.composer.clear()
        self.password.clear()
        self.device_info.setText("Geen geldige apparaatkoppeling.")

    def save_settings(self):
        try:
            value = Preferences(installation_id=self.preferences.installation_id, local_url=self.local_url.text(), remote_url=self.remote_url.text(), connection_mode=self.mode.currentData(),
                                theme=self.theme_choice.currentData(), language=self.language_choice.currentData(), provider=self.provider.currentData(),
                                log_level=self.log_choice.currentText(), **{key: item.isChecked() for key, item in self.setting_checks.items()}).validate()
            if self.running or self.login_busy:
                raise ValueError("Wacht op de login of stop het lopende antwoord voordat je instellingen wijzigt.")
            if value.startup != self.preferences.startup:
                Startup.set_enabled(value.startup)
            self.store.save(value)
            self.preferences = value
            self.manager.preferences = value
            self.notifications.enabled, self.notifications.answers = value.notifications, value.notify_answers
            self.setStyleSheet(stylesheet(value.theme))
            self.clear_private()
            self.manager.reset()
            self.password.clear()
            self.show_notice("Instellingen opgeslagen. " + ("English wordt na herstart toegepast op de hoofdnavigatie." if value.language == "en" else ""))
        except (ValueError, OSError) as error:
            self.show_notice(str(error))

    def system_info(self):
        try:
            value = self.permissions.run("system_info", {"system_info"} if self.local_permission.isChecked() else set())
            self.show_notice("Lokale systeeminformatie (niet verzonden): " + json.dumps(value))
        except PermissionError as error:
            self.show_notice(str(error))

    def notify(self, kind, text):
        if self.notifications.publish(kind, text):
            self.notification_list.clear()
            for stamp, message in self.notifications.items:
                self.notification_list.addItem(time.strftime("%H:%M", time.localtime(stamp)) + "  " + message)

    def deliver_notification(self, title, text):
        if self.tray.isVisible() and QSystemTrayIcon.supportsMessages():
            self.tray.showMessage(title, text, QSystemTrayIcon.MessageIcon.Information, 5000)

    def restore(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def restore_page(self, index):
        self.restore()
        self.navigate(index)

    def closeEvent(self, event):
        if not self.closing and self.preferences.minimize_to_tray and self.tray.isVisible():
            event.ignore()
            self.hide()
            self.notify("tray", "JARVIS blijft in het systeemvak. Kies Volledig afsluiten om de app te stoppen.")
        else:
            event.accept()
            self.shutdown()

    def shutdown(self):
        if self.closing:
            return
        self.closing = True
        self.voice_panel.close_voice()
        self.manager.stop()
        self.render_timer.stop()
        self.tray.hide()
        self.hide()
        # Do not destroy QThreads while requests are still unwinding.
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.timeout.connect(self.finish_shutdown)
        self.shutdown_timer.start(50)

    def finish_shutdown(self):
        if self.jobs.pool.activeThreadCount() == 0 and not self.voice.busy:
            self.shutdown_timer.stop()
            self.clear_private()
            QApplication.instance().quit()
