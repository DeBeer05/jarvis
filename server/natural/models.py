"""Versioned public settings; credentials and authentication switches are absent."""
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)


class General(StrictModel):
    assistant_name: str = Field(default="JARVIS", min_length=1, max_length=40, title="Naam assistent")
    address_name: str = Field(default="", max_length=60, title="Mijn aanspreeknaam")
    language: Literal["nl", "en"] = Field(default="nl", title="Taal")
    timezone: str = Field(default="Europe/Amsterdam", max_length=80, title="Tijdzone")
    @model_validator(mode="after")
    def valid_zone(self):
        try: ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError): raise ValueError("Onbekende tijdzone") from None
        return self


class Conversations(StrictModel):
    enabled: bool = Field(default=True, title="Natuurlijke gesprekken")
    continuous: bool = Field(default=False, title="Doorlopend luisteren na activeren")
    auto_listen: bool = Field(default=True, title="Na antwoord opnieuw luisteren")
    wake_word: str = Field(default="Hé JARVIS", min_length=2, max_length=60, title="Wake word")
    wake_sensitivity: float = Field(default=.6, ge=.1, le=1, title="Wake-gevoeligheid")
    push_to_talk: bool = Field(default=True, title="Spreekknop beschikbaar")
    automatic_end: bool = Field(default=True, title="Automatisch afsluiten")
    inactivity_seconds: int = Field(default=90, ge=10, le=1800, title="Inactiviteit (seconden)")
    maximum_seconds: int = Field(default=1800, ge=30, le=14400, title="Maximale sessieduur")
    resume: bool = Field(default=True, title="Eerdere gesprekken hervatten")
    default_mode: Literal["manual", "wake", "continuous"] = "manual"
    ending_phrases: list[str] = Field(default_factory=lambda:["Bedankt JARVIS", "Dat was alles", "Je mag stoppen", "Tot later", "Ga maar terug naar standby"], max_length=20, title="Afsluitzinnen")
    @model_validator(mode="after")
    def phrases(self):
        if any(not 1 <= len(p) <= 100 for p in self.ending_phrases): raise ValueError("Ongeldige afsluitzin")
        return self


class Listening(StrictModel):
    vad_threshold: float = Field(default=.015, ge=.001, le=.2, title="VAD-drempel")
    minimum_silence_ms: int = Field(default=500, ge=200, le=2500, title="Minimale stilte (ms)")
    normal_silence_ms: int = Field(default=900, ge=300, le=4000, title="Normale stilte (ms)")
    thinking_pause_ms: int = Field(default=2500, ge=500, le=8000, title="Denkpauze (ms)")
    adaptive: bool = Field(default=True, title="Adaptieve spreekbeurten")
    incremental_stt: bool = Field(default=False,title="Spraakherkenning tijdens het spreken",description="Verwerkt lange uitspraken in delen met overlap; voorlopig resultaat voert nooit een opdracht uit. Vereist adaptieve spreekbeurten.")
    maximum_listen_seconds: int = Field(default=60, ge=5, le=60, title="Maximale opname (s)")
    barge_in: bool = Field(default=False, title="Onderbreken met spraak")
    barge_in_sensitivity: float = Field(default=.7, ge=.1, le=1)
    echo_suppression: bool = Field(default=True, title="Echo-onderdrukking")
    noise_suppression: bool = Field(default=True, title="Ruisonderdrukking")
    background_filter: bool = True
    automatic_gain: bool = False
    indicator: bool = Field(default=True, title="Luisterindicator")
    activation_sound: bool = False
    ending_sound: bool = False
    @model_validator(mode="after")
    def ordered(self):
        if not self.minimum_silence_ms <= self.normal_silence_ms <= self.thinking_pause_ms:
            raise ValueError("Stiltedrempels moeten oplopen")
        return self


class Voice(StrictModel):
    stt_provider: Literal["whisper"] = "whisper"
    whisper_model: Literal["whisper-small","whisper-base","whisper-tiny"] = "whisper-small"
    tts_provider: Literal["auto","piper","supertonic","elevenlabs"] = "auto"
    mode: Literal["automatic","quality","fast","offline","manual","premium","budget","local"] = "automatic"
    elevenlabs_voice_id:str=Field(default='',pattern=r'^[A-Za-z0-9_-]{0,64}$')
    elevenlabs_model:Literal['eleven_flash_v2_5','eleven_multilingual_v2','eleven_v3','eleven_v4','eleven_v4_turbo','eleven_v3_conversational']='eleven_flash_v2_5'
    elevenlabs_stability:float=Field(default=.5,ge=0,le=1)
    elevenlabs_similarity:float=Field(default=.75,ge=0,le=1)
    elevenlabs_style:float=Field(default=0,ge=0,le=1)
    elevenlabs_speaker_boost:bool=True
    elevenlabs_daily_limit:int=Field(default=2000,ge=0,le=1000000)
    elevenlabs_monthly_limit:int=Field(default=10000,ge=0,le=10000000)
    elevenlabs_warning_percent:int=Field(default=80,ge=1,le=100)
    elevenlabs_sensitive_local:bool=True
    profile: Literal["classic_butler","modern_butler","deep_butler","cinematic","professional","friendly","fast","custom"] = "classic_butler"
    supertonic_voice: Literal["M1","M2","M3","M4","M5"] = "M1"
    steps:int=Field(default=8,ge=2,le=12,title="Supertonic kwaliteitsstappen")
    pause_ms:int=Field(default=180,ge=0,le=1000,title="Pauze tussen tekstblokken (ms)")
    fallback:bool=True
    voice: Literal["ronnie","mls"] = "ronnie"
    speaker: int = Field(default=0,ge=0,le=51,title="Piper-stemnummer (MLS 0–51)")
    speed: float = Field(default=1, ge=.7, le=1.5, title="Spreeksnelheid")
    volume: float = Field(default=.8, ge=0, le=1, title="Volume")
    buffer_ms: int = Field(default=120, ge=40, le=1000)
    streaming: bool = True
    processing: Literal["auto", "cpu", "cuda"] = "auto"
    cache: bool = True
    unload_after_seconds: int = Field(default=300, ge=30, le=3600)


class Personality(StrictModel):
    profile: Literal["classic_butler", "classic", "professional", "friendly", "informal", "humorous", "concise", "informative", "custom"] = "classic_butler"
    honorific: str=Field(default="meneer",max_length=30,title="Aanspreekvorm (leeg = uit)")
    honorific_frequency: Literal["off","occasionally","always"]="occasionally"
    confidence:int=Field(default=90,ge=0,le=100,title="Zelfverzekerde spreekstijl")
    formality: int = Field(default=80, ge=0, le=100)
    humor: int = Field(default=35, ge=0, le=100)
    sarcasm: int = Field(default=5, ge=0, le=100)
    friendliness: int = Field(default=75, ge=0, le=100)
    brevity: int = Field(default=90, ge=0, le=100)
    proactivity: int = Field(default=30, ge=0, le=100)
    initiative: int = Field(default=30, ge=0, le=100)
    followup_questions: int = Field(default=25, ge=0, le=100)
    technical_detail: int = Field(default=40, ge=0, le=100)
    speaking_style: str = Field(default="Natuurlijk Nederlands", max_length=300)
    custom_instructions: str = Field(default="", max_length=2000)


class AI(StrictModel):
    compact_context:bool=Field(default=True,title="Compacte context voor Oracle")
    processing:Literal["local","hybrid","cloud"]="hybrid"
    oracle_model:str=Field(default="",pattern=r"^[a-zA-Z0-9._:/-]{0,120}$")
    provider: Literal["auto", "gemini", "groq", "ollama", "oracle"] = "auto"
    fallback: Literal["none", "gemini", "groq", "ollama", "oracle"] = "ollama"
    automatic_selection: bool = True
    offline: bool = False
    gemini_model: str = Field(default="", pattern=r"^[a-zA-Z0-9._:/-]{0,120}$")
    groq_model: str = Field(default="", pattern=r"^[a-zA-Z0-9._:/-]{0,120}$")
    ollama_model: str = Field(default="", pattern=r"^[a-zA-Z0-9._:/-]{0,120}$")
    context_tokens: int = Field(default=6000, ge=256, le=12000)
    maximum_answer_tokens: int = Field(default=1024, ge=64, le=4096)
    streaming: bool = True
    temperature: float = Field(default=.2, ge=0, le=1)
    timeout_seconds: int = Field(default=60, ge=5, le=120)
    performance: Literal["saving", "balanced", "latency", "quality", "custom"] = "balanced"


class Memory(StrictModel):
    short_term: bool = True
    long_term: bool = True
    automatic: bool = False
    history: bool = True
    summaries: bool = True
    episodes: bool = Field(default=False,title="Eerdere gesprekken gericht terugvinden",description="Lokale FTS5-zoekfunctie in opgeslagen gebruikersuitspraken; volgt geschiedenis-, synchronisatie-, cloud- en vergeetbeleid.")
    retention_days: int = Field(default=365, ge=1, le=3650)
    semantic_search: bool = Field(default=False,description="Breidt FTS5 uit met een kleine Nederlandse woordenlijst. Geen embeddings of algemeen semantisch model.")
    synchronize: bool = True
    sensitive: bool = False
    prune_expired: bool = True
    context_items: int = Field(default=8, ge=0, le=20)


class Calendar(StrictModel):
    default_calendar: str = Field(default="primary", min_length=1, max_length=256)
    duration_minutes: int = Field(default=60, ge=5, le=1440)
    reminder_minutes: int = Field(default=30, ge=0, le=10080)
    buffer_minutes: int = Field(default=15, ge=0, le=240)
    workdays: list[int] = Field(default_factory=lambda:[0,1,2,3,4], max_length=7)
    work_start: str = Field(default="09:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    work_end: str = Field(default="17:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    conflicts: bool = True
    alternatives: bool = True
    neighboring: bool = True
    use_preferences: bool = True
    use_defaults: bool = True
    @model_validator(mode="after")
    def days(self):
        if any(type(d)!=int or not 0<=d<=6 for d in self.workdays) or len(set(self.workdays))!=len(self.workdays): raise ValueError("Ongeldige werkdagen")
        if self.work_end<=self.work_start: raise ValueError("Werkeinde moet na werkbegin liggen")
        return self


class Tasks(StrictModel):
    automatic_followups: bool = False
    followup_hours: int = Field(default=48, ge=1, le=720)
    combine_questions: bool = True
    resume: bool = True
    maximum_intents: int = Field(default=5, ge=1, le=8)


class Autonomy(StrictModel):
    profile: Literal["ask", "within_rules", "read_propose"] = "ask"
    actions: dict[str, Literal["allow", "ask", "block",'advise']] = Field(default_factory=dict, max_length=64)
    @model_validator(mode="after")
    def known(self):
        from server.automation.models import REGISTRY
        if any(k not in REGISTRY and k not in ("MemorySave", "MemoryUpdate") for k in self.actions): raise ValueError("Onbekende actie")
        if any(v=="allow" and k in REGISTRY and REGISTRY[k][1] for k,v in self.actions.items()):
            raise ValueError("Verplichte goedkeuring kan niet worden uitgeschakeld")
        return self


class Notifications(StrictModel):
    enabled: bool = True
    proactivity: Literal["off", "minimal", "normal", "proactive", "very_proactive"] = "normal"
    suggestions_per_hour: int = Field(default=3, ge=0, le=20)
    quiet_start: int = Field(default=22, ge=0, le=23)
    quiet_end: int = Field(default=7, ge=0, le=23)


class Presence(StrictModel):
    mode: Literal['normal','work','gaming','away','sleeping','travelling','private','emergency'] = 'normal'
    automatic: bool = Field(default=False,title='Automatisch omschakelen met toegestane apparaatsignalen')
    idle_seconds: int = Field(default=300,ge=60,le=7200,title='Afwezig na inactiviteit (s)')
    greetings: bool = Field(default=True,title='Eenmalige terugkomstbegroeting')
    sleep_schedule: bool = Field(default=False,title='Slapen vermoeden wanneer alle apparaten afwezig zijn')
    sleep_start: int = Field(default=23,ge=0,le=23)
    sleep_end: int = Field(default=7,ge=0,le=23)
    work_apps: list[str] = Field(default_factory=list,max_length=20,title='Werkprogramma’s (alleen procesnamen, lokaal vergelijken)')
    gaming_apps: list[str] = Field(default_factory=list,max_length=20,title='Games (alleen procesnamen, lokaal vergelijken)')
    @model_validator(mode='after')
    def apps(self):
        import re
        if any(not re.fullmatch(r'[\w .-]{1,70}\.exe',name,re.I) for name in self.work_apps+self.gaming_apps):
            raise ValueError('Gebruik alleen Windows-procesnamen, geen paden of opdrachten')
        return self


class Briefings(StrictModel):
    enabled:bool=Field(default=False,title='Geplande briefings inschakelen')
    morning:str=Field(default='08:00',pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$',title='Ochtendbriefing')
    evening:str=Field(default='22:00',pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$',title='Avondbriefing')
    on_return:bool=Field(default=True,title='Briefing bij terugkomst voorbereiden')
    calendar:bool=True
    email:bool=True
    weather:bool=Field(default=False,title='Open-Meteo weer gebruiken')
    news:bool=Field(default=False,title='NOS-nieuwskoppen gebruiken')
    traffic:bool=Field(default=False,title='NDW-verkeershinder in de regio gebruiken')
    location:str=Field(default='',max_length=100,title='Plaats voor weer (geen huisadres)')
    morning_channel:Literal['inbox','call']='inbox'
    evening_channel:Literal['inbox','call']='inbox'


class Privacy(StrictModel):
    cloud_memories: bool = False
    cloud_sensitive: Literal[False] = False
    retain_raw_audio: Literal[False] = False
    history_days: int = Field(default=365, ge=1, le=3650)
    diagnostic_days: int = Field(default=7, ge=1, le=30)


class Vision(StrictModel):
    enabled:bool=Field(default=False,title='Beeldanalyse inschakelen')
    provider:Literal['gemini','groq','ollama']='gemini'
    model:str=Field(default='',max_length=128,title='Bestaand beeldmodel (leeg gebruikt het ingestelde model)')
    cloud_allowed:bool=Field(default=False,title='Geselecteerde beelden mogen naar de gekozen cloudprovider')
    daily_requests:int=Field(default=10,ge=0,le=50,title='Maximale beeldvragen per dag')


class Diagnostics(StrictModel):
    enabled: bool = True
    latency: bool = True
    resources: bool = True
    maximum_events: int = Field(default=100, ge=10, le=1000)


class ResponseSettings(StrictModel):
    profile:Literal["auto","daily","technical","briefing","custom"]="auto"
    mode:Literal["auto","ultrashort","short","balanced","extended","full"]="auto"
    spoken:Literal["auto","ultrashort","short","balanced","extended","full"]="short"
    written:Literal["auto","ultrashort","short","balanced","extended","full"]="balanced"
    summaries:bool=True
    progressive:bool=True
    technical_detail:int=Field(default=40,ge=0,le=100)
    background:int=Field(default=20,ge=0,le=100)
    avoid_repetition:bool=True
    followup_questions:int=Field(default=10,ge=0,le=100)
    prioritize:bool=True
    brief_confirmations:bool=True
    email:bool=True
    calendar:bool=True
    news:bool=True
    messages:bool=True
    details_on_request:bool=True


class ActivityPlanning(StrictModel):
    enabled:bool=True
    mode:Literal['together','automatic','surprise','budget','relaxed','detailed']='together'
    default_budget:float=Field(default=0,ge=0,le=100000,title='Voorlopig totaalbudget (0 = onbekend)')
    maximum_distance_km:int=Field(default=100,ge=0,le=2000,title='Maximale reisafstand (km)')
    maximum_travel_minutes:int=Field(default=90,ge=0,le=1440,title='Maximale reistijd (minuten)')
    transport:Literal['unknown','car','train','bike','walk']='unknown'
    favorite_activities:list[str]=Field(default_factory=list,max_length=20)
    duration_minutes:int=Field(default=180,ge=15,le=1440)
    environment:Literal['any','inside','outside']='any'
    consider_weather:bool=True
    consider_calendar:bool=True
    include_travel:bool=True
    calculate_costs:bool=True
    suggest_restaurants:bool=True
    alternatives:int=Field(default=3,ge=2,le=4)
    initiative:Literal['suggest','choose']='suggest'
    questions:Literal['essential','balanced']='essential'
    automatic_reminders:bool=False
    communication:Literal['draft_only','propose_message']='draft_only'
    participant_preferences:dict[str,str]=Field(default_factory=dict,max_length=20)
    # No search, weather, ticket or route adapter is registered in phase 7.5.
    search_integrations:list[Literal['none']]=Field(default_factory=list,max_length=1)


class RoutingSettings(StrictModel):
    windows_device:str=Field(default='',pattern=r'^(?:[0-9a-f-]{36})?$',title='Standaardcomputer voor opdrachten vanaf andere apparaten')


class UserSettings(StrictModel):
    routing:RoutingSettings=Field(default_factory=RoutingSettings)
    vision:Vision=Field(default_factory=Vision)
    planning:ActivityPlanning=Field(default_factory=ActivityPlanning)
    responses: ResponseSettings=Field(default_factory=ResponseSettings)
    general: General = Field(default_factory=General)
    conversations: Conversations = Field(default_factory=Conversations)
    listening: Listening = Field(default_factory=Listening)
    voice: Voice = Field(default_factory=Voice)
    personality: Personality = Field(default_factory=Personality)
    ai: AI = Field(default_factory=AI)
    memory: Memory = Field(default_factory=Memory)
    calendar: Calendar = Field(default_factory=Calendar)
    tasks: Tasks = Field(default_factory=Tasks)
    autonomy: Autonomy = Field(default_factory=Autonomy)
    notifications: Notifications = Field(default_factory=Notifications)
    presence: Presence = Field(default_factory=Presence)
    briefings: Briefings = Field(default_factory=Briefings)
    privacy: Privacy = Field(default_factory=Privacy)
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)


class DeviceSettings(StrictModel):
    execution_policy:dict=Field(default_factory=dict,max_length=10,title="Windows-programma’s, documentmappen en mediabediening")
    execution_allowed:bool=Field(default=False,title="Gesloten Windows-opdrachten van uw andere apparaten ontvangen")
    input_device: int = Field(default=-1, ge=-1)
    output_device: int = Field(default=-1, ge=-1)
    muted: bool = False
    microphone_allowed: bool = False
    wake_enabled: bool = False
    keep_awake: bool = False
    presence_allowed: bool = Field(default=False,title='Aanwezigheidsstatus van dit apparaat delen')
    application_allowed: bool = Field(default=False,title='Actief programma lokaal met werk-/gamelijst vergelijken')
    handoff_allowed:bool=Field(default=False,title='Goedgekeurde opdrachten in telefoonapps klaarzetten')
    status_allowed:bool=Field(default=False,title='Batterijstatus met uw andere apparaten delen')
    notification_allowed:bool=Field(default=False,title='Aantallen meldingen delen (geen inhoud)')
    notification_packages:list[str]=Field(default_factory=list,max_length=20,title='Toegestane apppakketnamen voor meldingsaantallen')
    location_allowed:bool=Field(default=False,title='Optionele laatst bekende locatie delen (maximaal 24 uur bewaard)')
    screen_allowed:bool=Field(default=False,title='Zelf geselecteerde schermafbeeldingen mogen worden geanalyseerd')
    @model_validator(mode='after')
    def packages(self):
        from server.automation.windows import HostPolicy
        HostPolicy.model_validate(self.execution_policy)
        import re
        if any(not re.fullmatch(r'[a-z][a-z0-9_.]{2,100}',package) for package in self.notification_packages):raise ValueError('Ongeldige apppakketnaam')
        return self


class MemoryInput(StrictModel):
    category: Literal["preference", "person", "project", "work", "activity", "hobby", "habit", "decision", "technical", "location", "instruction", "conversation"] = "preference"
    content: str = Field(min_length=1, max_length=2000)
    key: str = Field(default="", max_length=100)
    kind: Literal["fact", "preference", "inference"] = "preference"
    confidence: float = Field(default=1, ge=0, le=1)
    sensitivity: Literal["normal", "sensitive"] = "normal"
    consent_sensitive: bool = False
    expires_at: float | None = Field(default=None, ge=0)
    status: Literal["active", "outdated", "proposed"] = "active"
