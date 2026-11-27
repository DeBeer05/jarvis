"""Owner-requested screen preview; capture stays on the existing Qt main thread."""
import base64
from uuid import uuid4

from PySide6.QtCore import QByteArray,QBuffer,QIODevice,QThread,Qt
from PySide6.QtGui import QColorSpace,QGuiApplication,QImage,QPixmap
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QLineEdit,QPlainTextEdit,QCheckBox


def capture_png(screen=None):
    app=QApplication.instance()
    if app is None or QThread.currentThread()!=app.thread():raise RuntimeError('Schermafbeeldingen worden alleen op de Qt-hoofdthread gemaakt')
    screen=screen or QGuiApplication.primaryScreen()
    if screen is None:raise RuntimeError('Geen scherm beschikbaar')
    image=screen.grabWindow(0).toImage()
    if image.isNull():raise RuntimeError('Schermafbeelding niet beschikbaar')
    if image.colorSpace().isValid():image=image.convertedToColorSpace(QColorSpace(QColorSpace.NamedColorSpace.SRgb))
    for width,height in ((1600,1000),(960,600),(640,400)):
        scaled=image.scaled(width,height,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_RGB888)
        scaled.setColorSpace(QColorSpace())
        encoded=QByteArray();buffer=QBuffer(encoded);buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not scaled.save(buffer,'PNG'):raise RuntimeError('Schermafbeelding kon niet worden verwerkt')
        buffer.close();data=bytes(encoded)
        if len(data)<=1_800_000:return data,scaled
    raise RuntimeError('Schermafbeelding blijft te groot')


class ScreenPanel(QWidget):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.device=None;self.image=None;self.serial=0;self.config=None;self.config_revision=None
        layout=QVBoxLayout(self)
        self.info=QLabel('Beeldanalyse staat standaard uit. Alleen een door u vastgelegde en gecontroleerde afbeelding wordt verzonden.');self.info.setWordWrap(True);self.info.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.info)
        self.allowed=QCheckBox('Zelf geselecteerde schermafbeeldingen op dit apparaat toestaan');self.allowed.setEnabled(False);self.allowed.toggled.connect(self.consent);layout.addWidget(self.allowed)
        bar=QHBoxLayout();layout.addLayout(bar)
        refresh=QPushButton('Instellingen vernieuwen');refresh.clicked.connect(self.refresh);bar.addWidget(refresh)
        self.capture=QPushButton('Maak schermvoorbeeld');self.capture.setEnabled(False);self.capture.clicked.connect(self.preview);bar.addWidget(self.capture)
        self.preview_label=QLabel();self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview_label.setMaximumHeight(360);layout.addWidget(self.preview_label)
        self.question=QLineEdit('Wat valt u op en kunt u mij hierbij helpen?');self.question.setMaxLength(600);layout.addWidget(self.question)
        self.send=QPushButton('Verzend dit gecontroleerde voorbeeld voor analyse');self.send.setEnabled(False);self.send.clicked.connect(self.analyze);layout.addWidget(self.send)
        self.report=QPlainTextEdit();self.report.setReadOnly(True);layout.addWidget(self.report)

    def clear(self):
        self.serial+=1;self.device=None;self.image=None;self.config=None;self.config_revision=None;self.preview_label.clear();self.report.clear()
        self.capture.setEnabled(False);self.send.setEnabled(False);self.allowed.setEnabled(False)
        self.allowed.blockSignals(True);self.allowed.setChecked(False);self.allowed.blockSignals(False)
        self.question.setText('Wat valt u op en kunt u mij hierbij helpen?')
        self.info.setText('Beeldanalyse staat standaard uit. Controleer uw eigen voorbeeld voordat u het verzendt.')

    def refresh(self):
        serial=self.serial
        def settings(document):
            if serial!=self.serial:return
            if self.config_revision!=document['revision']:self.image=None;self.preview_label.clear();self.send.setEnabled(False)
            self.config_revision=document['revision']
            self.config=document['settings']['vision']
            self.info.setText('Provider: '+self.config['provider']+'. Controleer het beeld op privégegevens voordat u het verzendt. Er wordt geen screenshot opgeslagen. Daglimiet: '+str(self.config['daily_requests'])+'.')
            self.window.call('GET','/api/v1/natural/device-settings',None,self.install)
        self.window.call('GET','/api/v1/natural/settings',None,settings)

    def install(self,document):
        self.device=document;enabled=document['settings']['screen_allowed'];self.allowed.setEnabled(True)
        self.allowed.blockSignals(True);self.allowed.setChecked(enabled);self.allowed.blockSignals(False)
        self.capture.setEnabled(bool(enabled and self.config and self.config['enabled']))

    def consent(self,enabled):
        if self.device is None:return
        document=self.device;settings={**document['settings'],'screen_allowed':enabled}
        self.window.call('PUT','/api/v1/natural/device-settings',{'revision':document['revision'],'settings':settings},self.install)
        if not enabled:self.image=None;self.preview_label.clear();self.send.setEnabled(False)

    def preview(self):
        try:
            self.image,image=capture_png();self.preview_label.setPixmap(QPixmap.fromImage(image).scaled(640,360,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));self.send.setEnabled(True)
        except RuntimeError as error:self.report.setPlainText(str(error))

    def analyze(self):
        if not self.image or self.config_revision is None:return
        serial=self.serial;self.send.setEnabled(False);self.report.setPlainText('Ik bekijk uw geselecteerde afbeelding, meneer.')
        body={'request_id':str(uuid4()),'settings_revision':self.config_revision,'image':base64.b64encode(self.image).decode(),'question':self.question.text()}
        def done(value):
            if serial!=self.serial:return
            report=value['report'];lines=[value['intro']]
            for key,label in (('observations','Waarnemingen'),('uncertainty','Onzekerheden'),('suggestions','Suggesties')):
                if report[key]:lines+=['',label,*('• '+item for item in report[key])]
            self.report.setPlainText('\n'.join(lines));self.image=None;self.preview_label.clear()
        def failed(error):
            if serial==self.serial:self.report.setPlainText(getattr(error,'message','Beeldanalyse niet bevestigd; geen nieuwe poging automatisch verstuurd.'))
        self.window.call('POST','/api/v1/natural/vision',body,done,failed)
