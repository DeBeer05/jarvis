"""A view on the server's conversation draft; edits use the existing chat route."""
from PySide6.QtWidgets import QDialog,QVBoxLayout,QPlainTextEdit,QLineEdit,QHBoxLayout,QPushButton,QLabel


class PlanningPanel(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window
        self.setWindowTitle('Uitjesplanning');self.resize(760,640)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('Voorstellen en bevestigde gegevens blijven herkenbaar. Wijzigingen bespreekt u in hetzelfde gesprek.'))
        self.overview=QPlainTextEdit();self.overview.setReadOnly(True);layout.addWidget(self.overview,1)
        self.edit=QLineEdit();self.edit.setPlaceholderText('Bijvoorbeeld: Doe toch zondag, met de trein en daarna ergens eten.');layout.addWidget(self.edit)
        actions=QHBoxLayout();layout.addLayout(actions)
        update=QPushButton('Wijziging bespreken');update.clicked.connect(self.apply);actions.addWidget(update)
        refresh=QPushButton('Vernieuwen');refresh.clicked.connect(self.refresh);actions.addWidget(refresh)
        close=QPushButton('Sluiten');close.clicked.connect(self.close);actions.addWidget(close)
        self.edit.returnPressed.connect(self.apply)

    def show_plan(self,data):
        self.overview.setPlainText(data.get('overview','Er is in dit gesprek nog geen uitjesplanning.'))

    def refresh(self):
        if not self.window.conversation or not self.window.principal:
            self.overview.setPlainText('Begin een planningsgesprek of open een eerder gesprek.');return
        conversation=self.window.conversation
        def loaded(body):
            if self.window.conversation==conversation and self.window.principal:self.show_plan(body.get('planning') or {})
        self.window.call('GET','/api/v1/natural/planning/'+conversation,None,loaded)

    def apply(self):
        text=self.edit.text().strip()
        if not text:return
        if self.window.running:self.window.show_notice('Wacht tot het antwoord klaar is of stop het eerst.');return
        self.edit.clear();self.window.send_voice_text(text)
