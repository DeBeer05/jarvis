"""Authenticated settings and memory UI. Network calls use the window's workers."""
from copy import deepcopy
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox,QComboBox,QDialog,QDialogButtonBox,QDoubleSpinBox,
    QFileDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QListWidget,QMessageBox,
    QPlainTextEdit,QPushButton,QScrollArea,QSpinBox,QTabWidget,QVBoxLayout,QWidget)

BASE="/api/v1/natural"
LABELS={"general":"Algemeen","conversations":"Gesprekken","listening":"Luisteren","voice":"Stem en audio",
    "personality":"Persoonlijkheid","ai":"AI en prestaties","memory":"Geheugen","calendar":"Agenda",
    "tasks":"Taken en automatiseringen","autonomy":"Zelfstandigheid en machtigingen","notifications":"Meldingen",
    "privacy":"Privacy","diagnostics":"Diagnostiek","profile":"Profiel","provider":"Primaire AI-provider",
    "fallback":"Fallback-provider","automatic_selection":"Automatische providerselectie","offline":"Alleen lokale AI",
    "context_tokens":"Contextbudget (geschatte tokens)","maximum_answer_tokens":"Maximale antwoordlengte (tokens)",
    "streaming":"Streaming","temperature":"Creativiteit","timeout_seconds":"AI-time-out (s)","performance":"Prestatieprofiel",
    "gemini_model":"Gemini-model","groq_model":"Groq-model","ollama_model":"Ollama-model",
    "formality":"Formaliteit","humor":"Humor","sarcasm":"Sarcasme","friendliness":"Vriendelijkheid",
    "brevity":"Beknoptheid","proactivity":"Proactiviteit","initiative":"Initiatief","followup_questions":"Vervolgvragen",
    "technical_detail":"Technisch detailniveau","speaking_style":"Spreekstijl","custom_instructions":"Eigen persoonlijkheidsinstructies",
    "short_term":"Kortetermijngeheugen","long_term":"Langetermijngeheugen","automatic":"Automatisch onthouden",
    "history":"Gespreksgeschiedenis","summaries":"Automatische samenvattingen","retention_days":"Bewaartermijn (dagen)",
    "semantic_search":"Semantisch zoeken","synchronize":"Synchroniseren","sensitive":"Gevoelig geheugen lokaal gebruiken",
    "prune_expired":"Verlopen herinneringen verwijderen","context_items":"Maximaal relevante herinneringen",
    "cloud_memories":"Gewone herinneringen naar cloud-AI toestaan","cloud_sensitive":"Gevoelige herinneringen naar cloud",
    "retain_raw_audio":"Ruwe microfoonaudio bewaren","history_days":"Gesprekken bewaren (dagen)","diagnostic_days":"Diagnostiek bewaren (dagen)",
    "default_calendar":"Standaardagenda","duration_minutes":"Standaard afspraakduur (minuten)","reminder_minutes":"Standaard herinnering (minuten)",
    "buffer_minutes":"Buffer tussen afspraken (minuten)","workdays":"Werkdagen","work_start":"Werkdag begint","work_end":"Werkdag eindigt",
    "conflicts":"Conflicten controleren","alternatives":"Alternatieven voorstellen","neighboring":"Naburige afspraken controleren",
    "use_preferences":"Persoonlijke voorkeuren gebruiken","use_defaults":"Standaardwaarden gebruiken","resume":"Onafgeronde opdrachten hervatten",
    "automatic_followups":"Automatische follow-ups","followup_hours":"Follow-uptermijn (uren)","combine_questions":"Ontbrekende vragen combineren",
    "maximum_intents":"Maximaal opdrachten per uitspraak","actions":"Regels per actie","enabled":"Ingeschakeld",
    "latency":"Latency meten","resources":"Resourcegebruik meten","maximum_events":"Maximaal diagnosegebeurtenissen",
    "default_mode":"Standaard gespreksmodus","wake_sensitivity":"Wake-wordgevoeligheid",
    "barge_in_sensitivity":"Onderbrekingsgevoeligheid","background_filter":"Achtergrondgeluid filteren","automatic_gain":"Automatische microfoongevoeligheid",
    "activation_sound":"Geluid bij activeren","ending_sound":"Geluid bij afsluiten","stt_provider":"Spraakherkenning",
    "whisper_model":"Whisper-model","tts_provider":"Spraakuitvoer","voice":"Stemprofiel","buffer_ms":"Audiobuffer (ms)",
    "processing":"Audioverwerking","cache":"Audiocache","unload_after_seconds":"Ongebruikte modellen vrijgeven na (s)",
    "suggestions_per_hour":"Maximaal suggesties per uur","quiet_start":"Stil vanaf (uur)","quiet_end":"Stil tot (uur)"}
VALUES={"auto":"Automatisch","none":"Geen","classic":"Klassieke JARVIS","professional":"Professioneel","friendly":"Vriendelijk",
    "informal":"Informeel","humorous":"Humoristisch","concise":"Kort en zakelijk","informative":"Uitgebreid en informatief","custom":"Aangepast",
    "saving":"Energiebesparend","balanced":"Gebalanceerd","latency":"Lage latency","quality":"Hoge kwaliteit",
    "ask":"Eerst toestemming vragen","within_rules":"Zelfstandig binnen regels","read_propose":"Alleen lezen en voorstellen",
    "allow":"Automatisch toestaan","block":"Blokkeren","manual":"Handmatig","wake":"Wake word","continuous":"Doorlopend",
    "off":"Uitgeschakeld","minimal":"Minimaal","normal":"Normaal","proactive":"Proactief","very_proactive":"Zeer proactief"}


def label(text):
    widget=QLabel(text);widget.setWordWrap(True);widget.setTextFormat(Qt.TextFormat.PlainText);return widget


class NaturalSettingsPanel(QWidget):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.document=None;self.schema=None;self.draft=None;self.category=None;self.controls={};self.dirty=False;self.loading=False
        layout=QVBoxLayout(self)
        self.status=label("Log in om je gespreksinstellingen en geheugen te openen.");layout.addWidget(self.status)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        settings=QWidget();self.tabs.addTab(settings,"Gespreksinstellingen");body=QVBoxLayout(settings)
        self.search=QLineEdit();self.search.setPlaceholderText("Zoek een instelling…");self.search.textChanged.connect(self.filter);body.addWidget(self.search)
        columns=QHBoxLayout();self.categories=QListWidget();self.categories.setMaximumWidth(230);self.categories.setWordWrap(True);self.categories.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.categories.currentRowChanged.connect(self.select_category);columns.addWidget(self.categories)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);columns.addWidget(self.scroll,1);body.addLayout(columns,1)
        actions=QHBoxLayout();body.addLayout(actions)
        for title,callback in (("Opslaan",self.save),("Annuleren",self.cancel),("Standaardwaarden",self.reset),("Vernieuwen",self.refresh),("Exporteren",self.export),("Importeren",self.import_data)):
            item=QPushButton(title);item.clicked.connect(callback);actions.addWidget(item)
        audio=QPushButton("Microfoon, luidspreker en stem testen");audio.clicked.connect(lambda:self.window.navigate(6));body.addWidget(audio)
        self.make_memory()
        self.clear()

    def clear(self):
        self.document=self.draft=self.schema=None;self.category=None;self.controls={};self.dirty=False
        self.keys=[];self.search.clear();self.memory_search.clear()
        self.categories.clear();self.memory_list.clear();self.memory_items=[];self.summary_list.clear();self.summary_text.clear();self.summary_items=[]
        self.scroll.takeWidget();self.status.setText("Log in om je instellingen en geheugen te openen.")
        self.tabs.setEnabled(False)

    def call(self,method,path,body,done):
        self.window.call(method,BASE+path,body,done,self.failed)

    def failed(self,error):
        self.loading=False
        self.status.setText("Niet opgeslagen of opgehaald. Controleer je verbinding en rechten. Bij een wijzigingsconflict: vernieuw eerst; je invoer blijft staan.")

    def refresh(self):
        if self.loading or not self.window.principal:return
        if self.dirty and QMessageBox.question(self,"Wijzigingen behouden","Niet-opgeslagen wijzigingen verwerpen en vernieuwen?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.loading=True;self.status.setText("Instellingen synchroniseren…")
        self.call("GET","/settings/schema",None,self.got_schema)

    def got_schema(self,data):
        self.schema=data;self.call("GET","/settings",None,self.loaded)

    def loaded(self,data):
        self.loading=True;selected=self.category
        self.document=data;self.draft=deepcopy(data["settings"]);self.dirty=False;self.controls={};self.category=None
        self.categories.clear();self.keys=list(self.schema["categories"])
        self.categories.addItems([self.schema["categories"][key] for key in self.keys]);self.tabs.setEnabled(True)
        self.categories.setCurrentRow(self.keys.index(selected) if selected in self.keys else 0)
        self.loading=False;self.status.setText(f"Gesynchroniseerd · versie {data['revision']} · microfoontoestemming blijft lokaal en de microfoon start niet automatisch.")
        if hasattr(self.window,"apply_natural_settings"):self.window.apply_natural_settings(data)

    def collect(self):
        if self.draft is not None and self.category:
            for key,read in self.controls.items():self.draft[self.category][key]=read()

    def changed(self,*_):
        if self.loading:return
        self.collect();self.dirty=self.draft!=self.document["settings"]
        self.status.setText("Niet-opgeslagen wijzigingen · kies Opslaan of Annuleren." if self.dirty else "Geen niet-opgeslagen wijzigingen.")

    def select_category(self,index):
        if index<0 or self.draft is None:return
        self.collect();self.category=self.keys[index];self.controls={}
        container=QWidget();form=QFormLayout(container);form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        definition=self.schema["user"]["properties"][self.category]
        definition=self.schema["user"]["$defs"][definition["$ref"].split("/")[-1]]
        previous=self.loading;self.loading=True
        for key,field in definition["properties"].items():
            title=field.get("title") or LABELS.get(key,key.replace("_"," "))
            if key in LABELS:title=LABELS[key]
            widget,read=self.field(field,self.draft[self.category][key]);self.controls[key]=read
            widget.setAccessibleName(title);widget.setToolTip(field.get("description",title))
            form.addRow(label(title),widget)
        self.loading=previous;self.scroll.setWidget(container)

    def field(self,field,value):
        if "const" in field:
            if type(value) is not bool:
                control=QLineEdit(str(value));control.setReadOnly(True);return control,lambda:value
            control=QCheckBox("Verplicht uitgeschakeld" if value is False else str(value));control.setChecked(bool(value));control.setEnabled(False);return control,lambda:value
        if "enum" in field:
            control=QComboBox()
            for item in field["enum"]:
                control.addItem(VALUES.get(item,str(item))+(" · niet geïnstalleerd" if item in field.get("x-unavailable",[]) else ""),item)
                control.model().item(control.count()-1).setEnabled(item not in field.get("x-unavailable",[]))
            control.setCurrentIndex(control.findData(value));control.currentIndexChanged.connect(self.changed);return control,control.currentData
        kind=field.get("type")
        if kind=="boolean":
            control=QCheckBox();control.setChecked(value);control.toggled.connect(self.changed);return control,control.isChecked
        if kind in ("integer","number"):
            control=QSpinBox() if kind=="integer" else QDoubleSpinBox()
            if kind=="number":control.setDecimals(3);control.setSingleStep(.05)
            control.setRange(field.get("minimum",0),field.get("maximum",100000));control.setValue(value);control.valueChanged.connect(self.changed);return control,control.value
        if kind=="array" and field.get("items",{}).get("type")=="integer":
            control=QWidget();row=QHBoxLayout(control);checks=[]
            for index,title in enumerate(("Ma","Di","Wo","Do","Vr","Za","Zo")):
                check=QCheckBox(title);check.setChecked(index in value);check.toggled.connect(self.changed);row.addWidget(check);checks.append(check)
            return control,lambda:[i for i,c in enumerate(checks) if c.isChecked()]
        if kind=="object":
            control=QWidget();form=QFormLayout(control);inputs={}
            # Registered tools are supplied by the server schema, never executable code.
            names=self.schema.get("actions",list(value))
            for name in names:
                combo=QComboBox()
                for action in ("ask","allow","block"):
                    if action=="allow" and name in self.schema.get("mandatory_approval",[]):continue
                    combo.addItem(VALUES[action],action)
                combo.setCurrentIndex(combo.findData(value.get(name,"ask")));combo.currentIndexChanged.connect(self.changed);form.addRow(label(name),combo);inputs[name]=combo
            return control,lambda:{k:c.currentData() for k,c in inputs.items() if k in value or c.currentData()!="ask"}
        multiline=kind=="array" or field.get("maxLength",0)>300
        if multiline:
            control=QPlainTextEdit("\n".join(value) if kind=="array" else value);control.setMaximumHeight(125);control.textChanged.connect(self.changed)
            return control,(lambda:[line.strip() for line in control.toPlainText().splitlines() if line.strip()]) if kind=="array" else control.toPlainText
        control=QLineEdit(value or "");control.setMaxLength(field.get("maxLength",256));control.textChanged.connect(self.changed);return control,control.text

    def filter(self,text):
        query=text.casefold().strip()
        for index,key in enumerate(getattr(self,"keys",[])):
            fields=" ".join(LABELS.get(name,name) for name in self.draft[key])
            self.categories.item(index).setHidden(query not in (self.categories.item(index).text()+" "+fields).casefold())

    def save(self):
        if not self.document:return
        self.collect();self.call("PUT","/settings",{"revision":self.document["revision"],"settings":self.draft},self.loaded)

    def cancel(self):
        if self.document:self.loaded(self.document)

    def reset(self):
        if not self.document:return
        if self.dirty:self.status.setText("Sla je wijzigingen eerst op of kies Annuleren voordat je standaardwaarden herstelt.");return
        if QMessageBox.question(self,"Standaardwaarden","Deze categorie terugzetten naar de standaardwaarden?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.call("POST","/settings/reset",{"revision":self.document["revision"],"category":self.category},self.loaded)

    def export(self):
        self.call("GET","/settings/export",None,lambda data:self.write_export(data,"jarvis-instellingen.json"))

    def write_export(self,data,name):
        path,_=QFileDialog.getSaveFileName(self,"Export opslaan",name,"JSON (*.json)")
        if path:
            try:
                with open(path,"w",encoding="utf-8") as stream:json.dump(data,stream,ensure_ascii=False,indent=2)
            except OSError:self.status.setText("Het exportbestand kon niet worden opgeslagen.")

    def import_data(self):
        if not self.document:return
        if self.dirty:self.status.setText("Sla je wijzigingen eerst op of kies Annuleren voordat je instellingen importeert.");return
        path,_=QFileDialog.getOpenFileName(self,"Instellingen importeren","","JSON (*.json)")
        if not path:return
        try:
            with open(path,"r",encoding="utf-8") as stream:document=json.loads(stream.read(100000))
            if not isinstance(document,dict) or document.get("scope")!="user":raise ValueError()
        except (OSError,ValueError):self.status.setText("Ongeldig instellingenbestand.");return
        if QMessageBox.question(self,"Instellingen vervangen","Globale instellingen vervangen door dit bestand?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.call("POST","/settings/import",{"revision":self.document["revision"],"document":document},self.loaded)

    def make_memory(self):
        page=QWidget();self.tabs.addTab(page,"Geheugen en samenvattingen");body=QVBoxLayout(page)
        body.addWidget(label("Herinneringen zijn je persoonlijke langetermijngeheugen. Wissen verwijdert ook afgeleide context; oorspronkelijke gesprekken blijven apart in Gesprekken staan."))
        search=QHBoxLayout();self.memory_search=QLineEdit();self.memory_search.setPlaceholderText("Herinneringen zoeken…");search.addWidget(self.memory_search)
        self.memory_category=QComboBox();self.memory_category.addItem("Alle categorieën","")
        for name in ("preference","person","project","work","activity","hobby","habit","decision","technical","location","instruction","conversation"):self.memory_category.addItem(name,name)
        search.addWidget(self.memory_category)
        find=QPushButton("Zoeken / vernieuwen");find.clicked.connect(self.load_memory);search.addWidget(find);body.addLayout(search)
        self.memory_list=QListWidget();body.addWidget(self.memory_list,1)
        actions=QHBoxLayout();body.addLayout(actions)
        for title,callback in (("Toevoegen",lambda:self.edit_memory(False)),("Wijzigen",lambda:self.edit_memory(True)),("Verwijderen",self.delete_memory),("Exporteren",lambda:self.call("GET","/memory/export",None,lambda data:self.write_export(data,"jarvis-geheugen.json"))),("Alles wissen",self.clear_memory)):
            item=QPushButton(title);item.clicked.connect(callback);actions.addWidget(item)
        self.summary_list=QComboBox();self.summary_list.currentIndexChanged.connect(self.select_summary);body.addWidget(self.summary_list)
        self.summary_text=QPlainTextEdit();self.summary_text.setPlaceholderText("Selecteer een gesprekssamenvatting…");self.summary_text.setMaximumHeight(110);body.addWidget(self.summary_text)
        summary=QPushButton("Samenvatting opslaan");summary.clicked.connect(self.save_summary);body.addWidget(summary)

    def load_memory(self):
        body={"query":self.memory_search.text()}
        if self.memory_category.currentData():body["category"]=self.memory_category.currentData()
        self.call("POST","/memory/search",body,self.memory_loaded)
        self.call("GET","/summaries",None,self.summaries_loaded)

    def memory_loaded(self,data):
        self.memory_items=data["items"];self.memory_list.clear()
        self.memory_list.addItems([f"{item['category']} · {item['content']} · {item['status']}" for item in self.memory_items])
        self.status.setText("Geheugen opgehaald."+(" Meer resultaten beschikbaar; verfijn je zoekopdracht." if data.get("has_more") else ""))

    def edit_memory(self,existing):
        index=self.memory_list.currentRow()
        if existing and index<0:return
        item=self.memory_items[index] if existing else None
        dialog=QDialog(self);dialog.setWindowTitle("Herinnering wijzigen" if item else "Herinnering toevoegen");dialog.resize(500,320)
        form=QFormLayout(dialog);content=QPlainTextEdit(item["content"] if item else "");form.addRow("Inhoud",content)
        category=QComboBox();category.addItems(["preference","person","project","work","activity","habit","hobby","decision","technical","location","instruction","conversation"])
        if item:category.setCurrentText(item["category"])
        form.addRow("Categorie",category)
        consent=QCheckBox("Ik geef expliciet toestemming voor deze gevoelige herinnering");form.addRow(consent)
        controls=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);controls.accepted.connect(dialog.accept);controls.rejected.connect(dialog.reject);form.addRow(controls)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        payload={"content":content.toPlainText(),"category":category.currentText(),"consent_sensitive":consent.isChecked()}
        if item:payload.update(revision=item["revision"],key=item["memory_key"],kind=item["kind"],confidence=item["confidence"],sensitivity=item["sensitivity"],expires_at=item["expires"],status=item["status"])
        if consent.isChecked():payload["sensitivity"]="sensitive"
        self.call("PUT" if item else "POST","/memory/"+item["id"] if item else "/memory",payload,lambda _:self.load_memory())

    def delete_memory(self):
        index=self.memory_list.currentRow()
        if index<0:return
        if QMessageBox.question(self,"Herinnering verwijderen","De geselecteerde herinnering verwijderen? Oorspronkelijke gesprekken blijven bewaard.",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.call("DELETE","/memory/"+self.memory_items[index]["id"],None,lambda _:self.load_memory())

    def clear_memory(self):
        if QMessageBox.question(self,"Alle herinneringen wissen","Alle persoonlijke herinneringen en samenvattingen wissen? Gesprekken blijven afzonderlijk bestaan.",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.call("POST","/memory/clear",{"confirmed":True},lambda _:self.load_memory())

    def summaries_loaded(self,data):
        self.summary_items=data["items"];self.summary_list.clear();self.summary_list.addItems(["Gesprek "+item["conversation_id"][:8] for item in self.summary_items]);self.select_summary(self.summary_list.currentIndex())

    def select_summary(self,index):
        self.summary_text.setPlainText(self.summary_items[index]["content"] if 0<=index<len(getattr(self,"summary_items",[])) else "")

    def save_summary(self):
        index=self.summary_list.currentIndex()
        if index<0:return
        item=self.summary_items[index];self.call("PUT","/summaries/"+item["id"],{"revision":item["revision"],"content":self.summary_text.toPlainText()},lambda _:self.load_memory())
