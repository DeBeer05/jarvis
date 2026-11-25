"""Authenticated settings and memory UI. Network calls use the window's workers."""
from copy import deepcopy
import json
import base64

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox,QComboBox,QDialog,QDialogButtonBox,QDoubleSpinBox,
    QFileDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QListWidget,QMessageBox,
    QPlainTextEdit,QPushButton,QScrollArea,QSpinBox,QTabWidget,QVBoxLayout,QWidget)

BASE="/api/v1/natural"
LABELS={"general":"Algemeen","conversations":"Gesprekken","listening":"Luisteren",
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
    "semantic_search":"Verwante trefwoorden (licht)","synchronize":"Synchroniseren","sensitive":"Gevoelig geheugen lokaal gebruiken",
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
        self.make_studio()
        self.make_contacts()
        self.make_memory()
        self.make_diagnostics()
        self.clear()

    def clear(self):
        self.document=self.draft=self.schema=None;self.category=None;self.controls={};self.dirty=False
        self.keys=[];self.search.clear();self.memory_search.clear()
        self.categories.clear();self.memory_list.clear();self.memory_items=[];self.summary_list.clear();self.summary_text.clear();self.summary_items=[]
        self.contact_items=[];self.contact_list.clear();self.contact_search.clear()
        self.studio_queue=[];self.studio_serial=getattr(self,"studio_serial",0)+1
        self.studio_text.setPlainText("Goedemorgen, meneer. Uw agenda is bijgewerkt en u heeft twee belangrijke berichten ontvangen.")
        self.diagnostic_document=None
        for value in self.diagnostic_labels.values():value.setText("Nog niet gemeten")
        self.scroll.takeWidget();self.status.setText("Log in om je instellingen en geheugen te openen.")
        self.tabs.setEnabled(False)

    def call(self,method,path,body,done):
        if path.startswith("/settings"):
            self.loading=True;self.tabs.setEnabled(False)
        self.window.call(method,BASE+path,deepcopy(body),done,self.failed)

    def failed(self,error):
        self.loading=False
        self.tabs.setEnabled(bool(self.document and self.window.principal))
        self.status.setText("Niet opgeslagen of opgehaald. Controleer je verbinding en rechten. Bij een wijzigingsconflict: vernieuw eerst; je invoer blijft staan.")

    def refresh(self):
        if self.loading or not self.window.principal:return
        if self.dirty and QMessageBox.question(self,"Wijzigingen behouden","Niet-opgeslagen wijzigingen verwerpen en vernieuwen?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.loading=True;self.status.setText("Instellingen synchroniseren…")
        self.call("GET","/settings/schema",None,self.got_schema)

    def got_schema(self,data):
        LABELS.update(data.get("labels",{}));VALUES.update(data.get("values",{}))
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
        try:self.collect()
        except ValueError:
            self.dirty=True;self.status.setText('Gebruik voor iedere deelnemer: naam: voorkeur.');return
        self.dirty=self.draft!=self.document["settings"]
        self.status.setText("Niet-opgeslagen wijzigingen · kies Opslaan of Annuleren." if self.dirty else "Geen niet-opgeslagen wijzigingen.")

    def select_category(self,index):
        if index<0 or self.draft is None:return
        try:self.collect()
        except ValueError:self.status.setText('Controleer eerst de voorkeuren per deelnemer.');return
        self.category=self.keys[index];self.controls={}
        container=QWidget();form=QFormLayout(container);form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        definition=self.schema["user"]["properties"][self.category]
        definition=self.schema["user"]["$defs"][definition["$ref"].split("/")[-1]]
        previous=self.loading;self.loading=True
        for key,field in definition["properties"].items():
            title=field.get("title") or LABELS.get(key,key.replace("_"," "))
            if key in LABELS:title=LABELS[key]
            if self.category=='planning':title=self.schema.get('labels',{}).get(key,title)
            widget,read=self.field(field,self.draft[self.category][key]);self.controls[key]=read
            widget.setAccessibleName(title);widget.setToolTip(field.get("description",title))
            form.addRow(label(title),widget)
        self.loading=previous;self.scroll.setWidget(container)
        if self.category=="personality":
            preview=QPushButton("Voorbeeldgesprek testen");preview.clicked.connect(self.preview_personality)
            form.addRow(preview)

    def preview_personality(self):
        if not self.document:return
        self.collect()
        self.status.setText("Voorbeeld genereren met de ingestelde AI-provider…")
        def show(data):
            dialog=QDialog(self);dialog.setWindowTitle("Persoonlijkheidsvoorbeeld · niet opgeslagen")
            layout=QVBoxLayout(dialog);text=QPlainTextEdit(data["message"]);text.setReadOnly(True);layout.addWidget(text)
            close=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);close.rejected.connect(dialog.reject);layout.addWidget(close)
            dialog.resize(560,300);dialog.exec()
            self.status.setText("Voorbeeld voltooid; je wijzigingen zijn nog niet opgeslagen." if self.dirty else "Voorbeeld voltooid; er zijn geen taken uitgevoerd.")
        self.call("POST","/personality/preview",{"personality":self.draft["personality"]},show)

    def field(self,field,value):
        if "const" in field:
            if type(value) is not bool:
                control=QLineEdit(str(value));control.setReadOnly(True);return control,lambda:value
            control=QCheckBox("Verplicht uitgeschakeld" if value is False else str(value));control.setChecked(bool(value));control.setEnabled(False);return control,lambda:value
        if "enum" in field:
            control=QComboBox()
            for item in field["enum"]:
                control.addItem(self.schema.get('values',{}).get(item,VALUES.get(item,str(item)))+(" · niet geïnstalleerd" if item in field.get("x-unavailable",[]) else ""),item)
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
            if field.get('additionalProperties',{}).get('type')=='string':
                control=QPlainTextEdit('\n'.join(name+': '+preference for name,preference in value.items()));control.setPlaceholderText('Sam: houdt van wandelen');control.setMaximumHeight(125);control.textChanged.connect(self.changed)
                def preferences():
                    result={}
                    for line in control.toPlainText().splitlines():
                        if not line.strip():continue
                        name,separator,preference=line.partition(':')
                        if not separator or not name.strip() or not preference.strip():raise ValueError('Gebruik naam: voorkeur')
                        result[name.strip()]=preference.strip()
                    return result
                return control,preferences
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
        if not self.document or self.loading:return
        try:self.collect()
        except ValueError:self.status.setText('Controleer eerst de voorkeuren per deelnemer.');return
        self.call("PUT","/settings",{"revision":self.document["revision"],"settings":self.draft},self.loaded)

    def make_diagnostics(self):
        page=QWidget();self.tabs.addTab(page,"Diagnostiek");body=QVBoxLayout(page)
        body.addWidget(label("Metingen bevatten geen gespreksinhoud of sleutels. CPU/RAM gelden voor de server en de eigen spraakhelper. De eerste CPU-meting vereist een volgende verversing."))
        form=QFormLayout();self.diagnostic_labels={}
        for key,title in (("server","Server en database"),("provider","Laatst gebruikte AI"),("voice","STT en TTS"),("microphone","Lokale microfoon"),("transport","Verbinding"),("session","Spraakgesprek"),("memory","Geheugen"),("integration","Google-koppeling"),("cpu","CPU server (één kern = 100%)"),("ram","RAM server / spraakhelper"),("gpu","GPU"),("stt","STT (server)"),("ai","Eerste AI-tekst (server)"),("tts","TTS-aanvraag (server)"),("audio","Eerste afgespeelde audio (client)"),("total","Totale antwoordtijd (server)"),("context","Contextgrootte (geschatte tokens)"),("interruptions","Onderbrekingen / geweigerde activaties"),("errors","Laatste foutcodes")):
            value=label("Nog niet gemeten");form.addRow(title,value);self.diagnostic_labels[key]=value
        scroll=QScrollArea();scroll.setWidgetResizable(True);content=QWidget();content.setLayout(form);scroll.setWidget(content);body.addWidget(scroll,1)
        actions=QHBoxLayout();body.addLayout(actions)
        refresh=QPushButton("Metingen vernieuwen");refresh.clicked.connect(self.refresh_diagnostics);actions.addWidget(refresh)
        export=QPushButton("Diagnostiek exporteren");export.clicked.connect(lambda:self.call("GET","/diagnostics",None,lambda data:self.write_export(data,"jarvis-diagnostiek.json")));actions.addWidget(export)

    def refresh_diagnostics(self):self.call("GET","/diagnostics",None,self.diagnostics_loaded)

    def diagnostics_loaded(self,data):
        self.diagnostic_document=data;labels=self.diagnostic_labels
        labels["server"].setText("Online · database gecontroleerd")
        labels["provider"].setText(data.get("active_provider") or "Nog geen AI-antwoord")
        capabilities=data["voice"]["capabilities"]
        labels["voice"].setText("Spraakengine bezig" if data["voice"]["inference_busy"] else "Runtime aanwezig" if capabilities["runtime_installed"] else "Runtime niet geïnstalleerd")
        voice=getattr(self.window,"voice",None)
        labels["microphone"].setText(voice.state if voice else "Apparaatspecifiek")
        labels["transport"].setText("Geauthenticeerde HTTP/SSE · WebSocket nog niet geconfigureerd")
        sessions=data.get("sessions",[]);labels["session"].setText(", ".join(item["state"] for item in sessions[:3]) or "Standby")
        labels["memory"].setText(str(data.get("memory_counts",{}).get("active",0))+" actieve herinneringen")
        labels["integration"].setText("Gekoppeld" if data.get("integrations",{}).get("google_connected") else "Niet gekoppeld")
        resources=data.get("resources") or {}
        cpu=resources.get("cpu_one_core_percent");labels["cpu"].setText(f"{cpu:.1f}%" if cpu is not None else "Nog niet gemeten / uitgeschakeld")
        mib=lambda value:f"{value/1048576:.1f} MiB" if value is not None else "Niet gemeten"
        labels["ram"].setText(mib(resources.get("resident_bytes"))+" / "+mib(resources.get("voice_helper_resident_bytes")))
        gpu=resources.get("gpu_percent");labels["gpu"].setText(f"{gpu:.0f}% (hele machine)" if gpu is not None else "Niet gemeten")
        for key,metric in (("stt","stt_ms"),("ai","ai_first_token_ms"),("tts","tts_ms"),("audio","native_first_audio_ms"),("total","response_total_ms")):
            value=data["latency"].get(metric);labels[key].setText(f"{value/1000:.3f} s" if value is not None else "Nog niet gemeten")
        tokens=data["latency"].get("context_tokens");labels["context"].setText(str(round(tokens)) if tokens is not None else "Nog niet gemeten")
        events=data.get("events",[])
        count=lambda event:sum(row.get("metric") or 0 for row in events if row["event"]==event)
        labels["interruptions"].setText(f"{count('interruption'):.0f} / {count('rejected_interruption')+count('wake_miss'):.0f} (bewaarde meetperiode)")
        labels["errors"].setText(", ".join(row["code"] for row in events if row.get("code")) or "Geen bewaarde foutcodes")

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
        status=QComboBox()
        for title,value in (("Actief","active"),("Voorstel: nog niet gebruiken","proposed"),("Verouderd","outdated")):status.addItem(title,value)
        status.setCurrentIndex(max(0,status.findData(item["status"] if item else "active")));form.addRow("Status",status)
        consent=QCheckBox("Ik geef expliciet toestemming voor deze gevoelige herinnering");form.addRow(consent)
        controls=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);controls.accepted.connect(dialog.accept);controls.rejected.connect(dialog.reject);form.addRow(controls)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        payload={"content":content.toPlainText(),"category":category.currentText(),"consent_sensitive":consent.isChecked()}
        if item:payload.update(revision=item["revision"],key=item["memory_key"],kind=item["kind"],confidence=item["confidence"],sensitivity=item["sensitivity"],expires_at=item["expires"],status=item["status"])
        if consent.isChecked():payload["sensitivity"]="sensitive"
        payload["status"]=status.currentData()
        self.call("PUT" if item else "POST","/memory/"+item["id"] if item else "/memory",payload,self.memory_changed)

    def delete_memory(self):
        index=self.memory_list.currentRow()
        if index<0:return
        if QMessageBox.question(self,"Herinnering verwijderen","De geselecteerde herinnering verwijderen? Oorspronkelijke gesprekken blijven bewaard.",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.call("DELETE","/memory/"+self.memory_items[index]["id"],None,self.memory_changed)

    def clear_memory(self):
        if QMessageBox.question(self,"Alle herinneringen wissen","Alle persoonlijke herinneringen en samenvattingen wissen? Gesprekken blijven afzonderlijk bestaan.",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.call("POST","/memory/clear",{"confirmed":True},self.memory_changed)

    def memory_changed(self,_):
        if hasattr(self.window,"voice"):
            if self.window.voice.responding:self.window.voice_stop()
            with self.window.voice.cache_lock:self.window.voice.cache.clear()
        self.load_memory()

    def summaries_loaded(self,data):
        self.summary_items=data["items"];self.summary_list.clear();self.summary_list.addItems(["Gesprek "+item["conversation_id"][:8] for item in self.summary_items]);self.select_summary(self.summary_list.currentIndex())

    def select_summary(self,index):
        self.summary_text.setPlainText(self.summary_items[index]["content"] if 0<=index<len(getattr(self,"summary_items",[])) else "")

    def save_summary(self):
        index=self.summary_list.currentIndex()
        if index<0:return
        item=self.summary_items[index];self.call("PUT","/summaries/"+item["id"],{"revision":item["revision"],"content":self.summary_text.toPlainText()},lambda _:self.load_memory())


    def make_contacts(self):
        page=QWidget();self.tabs.addTab(page,"Adresboek");body=QVBoxLayout(page)
        body.addWidget(label("Sla bekende ontvangers op. Zeg bijvoorbeeld: Maak een mail aan Noah dat ik vrijdag beschikbaar ben. Controleer het volledige e-mailadres in het verzendvoorstel."))
        self.contact_search=QLineEdit();self.contact_search.setPlaceholderText("Zoek naam, alias of e-mailadres…");self.contact_search.textChanged.connect(self.filter_contacts);body.addWidget(self.contact_search)
        self.contact_list=QListWidget();body.addWidget(self.contact_list,1)
        actions=QHBoxLayout();body.addLayout(actions)
        for title,callback in (("Vernieuwen",self.load_contacts),("Toevoegen",lambda:self.edit_contact(False)),("Wijzigen",lambda:self.edit_contact(True)),("Verwijderen",self.delete_contact)):
            button=QPushButton(title);button.clicked.connect(callback);actions.addWidget(button)
        self.tabs.currentChanged.connect(lambda _:self.load_contacts() if self.tabs.currentWidget() is page and self.document else None)

    def load_contacts(self):self.call("GET","/contacts",None,self.contacts_loaded)

    def contacts_loaded(self,data):
        self.contact_items=data["items"];self.filter_contacts();self.status.setText("Adresboek gesynchroniseerd.")

    def filter_contacts(self):
        query=self.contact_search.text().casefold();self.contact_list.clear()
        self.visible_contacts=[item for item in getattr(self,"contact_items",[]) if query in (item["name"]+" "+item["email"]+" "+" ".join(item["aliases"])).casefold()]
        self.contact_list.addItems([item["name"]+" — "+item["email"]+(" · "+", ".join(item["aliases"]) if item["aliases"] else "") for item in self.visible_contacts])

    def edit_contact(self,existing):
        index=self.contact_list.currentRow()
        if existing and index<0:return
        item=self.visible_contacts[index] if existing else None
        dialog=QDialog(self);dialog.setWindowTitle("Contact wijzigen" if item else "Contact toevoegen");dialog.resize(500,260)
        form=QFormLayout(dialog);name=QLineEdit(item["name"] if item else "");email=QLineEdit(item["email"] if item else "");aliases=QPlainTextEdit("\n".join(item["aliases"]) if item else "")
        form.addRow("Naam",name);form.addRow("E-mailadres",email);form.addRow("Aliassen (één per regel, maximaal 8)",aliases)
        error=label("");form.addRow(error)
        controls=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);controls.rejected.connect(dialog.reject);form.addRow(controls)
        def save():
            payload={"name":name.text().strip(),"email":email.text().strip(),"aliases":[value.strip() for value in aliases.toPlainText().splitlines() if value.strip()]}
            if item:payload["revision"]=item["revision"]
            controls.setEnabled(False)
            def done(_):dialog.accept();self.load_contacts()
            def failed(_):controls.setEnabled(True);error.setText("Niet opgeslagen. Controleer de velden en verbinding. Bij een wijzigingsconflict: sluit en vernieuw het adresboek.")
            self.window.call("PUT" if item else "POST",BASE+"/contacts"+("/"+item["id"] if item else ""),payload,done,failed)
        controls.accepted.connect(save);dialog.exec()

    def delete_contact(self):
        index=self.contact_list.currentRow()
        if index<0:return
        item=self.visible_contacts[index]
        if QMessageBox.question(self,"Contact verwijderen","Dit contact uit het adresboek verwijderen? Bestaande mailvoorstellen blijven ongewijzigd.",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.call("DELETE","/contacts/"+item["id"]+"?revision="+str(item["revision"]),None,lambda _:self.load_contacts())


    def make_studio(self):
        page=QWidget();self.tabs.addTab(page,"Voice Studio");body=QVBoxLayout(page)
        body.addWidget(label("Vergelijk vaste stemmen met dezelfde tekst. Profielen zijn instellingen, geen afzonderlijk getrainde stemmen. Dit opent de microfoon niet. Alle ondersteunde stemmen werken lokaal; pitch en expressiviteit zijn niet beschikbaar."))
        self.studio_voice=QComboBox();body.addWidget(self.studio_voice)
        self.studio_text=QPlainTextEdit("Goedemorgen, meneer. Uw agenda is bijgewerkt en u heeft twee belangrijke berichten ontvangen.");self.studio_text.setMaximumHeight(100);body.addWidget(self.studio_text)
        self.studio_speed=QDoubleSpinBox();self.studio_speed.setRange(.7,1.5);self.studio_speed.setSingleStep(.05);self.studio_speed.setValue(.95)
        speed=QFormLayout();speed.addRow("Spreeksnelheid",self.studio_speed)
        self.studio_volume=QDoubleSpinBox();self.studio_volume.setRange(0,1);self.studio_volume.setSingleStep(.1);self.studio_volume.setValue(.8);speed.addRow("Volume",self.studio_volume);body.addLayout(speed)
        self.studio_metrics=label("Nog niet gemeten");body.addWidget(self.studio_metrics)
        actions=QHBoxLayout();body.addLayout(actions)
        for title,callback in (("Stemmen ophalen",self.load_studio),("Beluisteren",lambda:self.preview_studio(False)),("Vergelijk achter elkaar",lambda:self.preview_studio(True)),("Als favoriete stem opslaan",self.favorite_studio),("Stop",self.stop_studio)):
            button=QPushButton(title);button.clicked.connect(callback);actions.addWidget(button)
        self.studio_queue=[];self.studio_serial=0;self.studio_connected=False
        self.tabs.currentChanged.connect(lambda _:self.load_studio() if self.tabs.currentWidget() is page and self.document else None)

    def load_studio(self):
        if hasattr(self.window,"voice") and not self.studio_connected:
            self.window.voice.preview_finished.connect(self.next_studio);self.studio_connected=True
        def loaded(data):
            self.studio_voice.clear()
            for provider in data["providers"]:
                for voice in provider["voices"]:
                    if voice["available"]:self.studio_voice.addItem(provider["name"]+" · "+voice["name"],(provider["id"],voice["id"]))
            self.status.setText("Voice Studio: beschikbare lokale stemmen opgehaald.")
        self.call("GET","/voice-studio",None,loaded)

    def studio_options(self,selection):
        voice=deepcopy(self.document["settings"]["voice"]);provider,name=selection
        voice.update(profile="custom",mode="manual",tts_provider=provider,speed=self.studio_speed.value(),volume=self.studio_volume.value())
        voice["supertonic_voice" if provider=="supertonic" else "voice"]=name
        return voice

    def favorite_studio(self):
        if not self.document or not self.studio_voice.currentData():return
        if self.dirty:self.status.setText("Sla je overige wijzigingen eerst op of annuleer ze.");return
        voice=self.studio_options(self.studio_voice.currentData())
        self.call("PATCH","/settings/voice",{"revision":self.document["revision"],"changes":voice},self.loaded)

    def stop_studio(self):
        self.studio_queue=[];self.studio_serial+=1
        if hasattr(self.window,"voice"):self.window.voice.stop()

    def preview_studio(self,compare):
        if not self.document or not hasattr(self.window,"voice") or self.window.running:return
        self.stop_studio()
        self.studio_queue=[self.studio_voice.itemData(i) for i in range(self.studio_voice.count())] if compare else [self.studio_voice.currentData()]
        self.next_studio()

    def next_studio(self):
        if not self.studio_queue:return
        selection=self.studio_queue.pop(0)
        if not selection:return
        text=self.studio_text.toPlainText().strip()
        if not 1<=len(text)<=350:self.status.setText("Gebruik 1 tot 350 tekens voor het stemvoorbeeld.");self.stop_studio();return
        serial=self.studio_serial;voice=self.studio_options(selection);self.status.setText("Stemvoorbeeld genereren…")
        def ready(data):
            if serial!=self.studio_serial:return
            self.studio_metrics.setText(f"{data['provider']} · {data.get('voice',selection[1])} · eerste audio {data['seconds']:.2f} s · RAM helper {data.get('runtime_stats',{}).get('ram_bytes',0)/1048576:.1f} MiB")
            self.window.voice.play_preview(base64.b64decode(data["audio"],validate=True),voice["volume"])
        self.window.voice.switch_worker()
        worker=self.window.voice.worker
        if not getattr(worker,"centralized",False):self.status.setText("Verbind met de server om Voice Studio te gebruiken.");self.stop_studio();return
        def generate(_):
            raw=worker.request(BASE+"/voice-studio/preview",body={"text":text,"voice":voice},valid=lambda:serial==self.studio_serial)
            return json.loads(raw)
        def failed(error):
            if serial==self.studio_serial:self.studio_queue=[];self.failed(error)
        self.window.jobs.submit(generate,ready,failed)
