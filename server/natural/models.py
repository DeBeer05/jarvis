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
    tts_provider: Literal["piper"] = "piper"
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
    profile: Literal["classic", "professional", "friendly", "informal", "humorous", "concise", "informative", "custom"] = "friendly"
    formality: int = Field(default=35, ge=0, le=100)
    humor: int = Field(default=35, ge=0, le=100)
    sarcasm: int = Field(default=5, ge=0, le=100)
    friendliness: int = Field(default=75, ge=0, le=100)
    brevity: int = Field(default=75, ge=0, le=100)
    proactivity: int = Field(default=30, ge=0, le=100)
    initiative: int = Field(default=30, ge=0, le=100)
    followup_questions: int = Field(default=25, ge=0, le=100)
    technical_detail: int = Field(default=40, ge=0, le=100)
    speaking_style: str = Field(default="Natuurlijk Nederlands", max_length=300)
    custom_instructions: str = Field(default="", max_length=2000)


class AI(StrictModel):
    provider: Literal["auto", "gemini", "groq", "ollama"] = "auto"
    fallback: Literal["none", "gemini", "groq", "ollama"] = "ollama"
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
    actions: dict[str, Literal["allow", "ask", "block"]] = Field(default_factory=dict, max_length=30)
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


class Privacy(StrictModel):
    cloud_memories: bool = False
    cloud_sensitive: Literal[False] = False
    retain_raw_audio: Literal[False] = False
    history_days: int = Field(default=365, ge=1, le=3650)
    diagnostic_days: int = Field(default=7, ge=1, le=30)


class Diagnostics(StrictModel):
    enabled: bool = True
    latency: bool = True
    resources: bool = True
    maximum_events: int = Field(default=100, ge=10, le=1000)


class UserSettings(StrictModel):
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
    privacy: Privacy = Field(default_factory=Privacy)
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)


class DeviceSettings(StrictModel):
    input_device: int = Field(default=-1, ge=-1)
    output_device: int = Field(default=-1, ge=-1)
    muted: bool = False
    microphone_allowed: bool = False
    wake_enabled: bool = False
    keep_awake: bool = False


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
