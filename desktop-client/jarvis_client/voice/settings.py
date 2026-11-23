from dataclasses import asdict, dataclass
import json
from pathlib import Path

from jarvis_client.settings import data_directory


@dataclass
class VoiceSettings:
    models: str = ""
    input_device: int = -1
    output_device: int = -1
    input_gain: float = 1.0
    output_gain: float = 0.8
    sensitivity: float = 0.5
    silence_seconds: float = 1.2
    max_seconds: int = 60
    followup_seconds: int = 0
    model: str = "whisper-small"
    device: str = "auto"
    provider: str = "piper"
    voice: str = "ronnie"
    speaker: int = 0
    speed: float = 1.0
    profile: str = "desktop"
    cache: bool = True
    ptt_shortcut: str = "Ctrl+Space"
    stop_shortcut: str = "Ctrl+Shift+Space"
    global_hotkeys: bool = False

    def validate(self):
        if self.model not in ("whisper-small", "whisper-base", "whisper-tiny") or self.device not in ("auto", "cpu", "cuda") or self.provider != "piper" or self.profile not in ("desktop", "light") or self.voice not in ("ronnie", "mls"):
            raise ValueError("Kies een ondersteund lokaal spraakprofiel.")
        for value, low, high in ((self.input_gain, 0.1, 3), (self.output_gain, 0, 1), (self.sensitivity, 0, 1),
                                 (self.silence_seconds, 0.4, 4), (self.max_seconds, 5, 120),
                                 (self.followup_seconds, 0, 30), (self.speaker, 0, 51), (self.speed, 0.7, 1.5)):
            if not low <= value <= high:
                raise ValueError("Spraakinstelling buiten het toegestane bereik.")
        if self.input_device < -1 or self.output_device < -1:
            raise ValueError("Ongeldig audioapparaat.")
        if not self.ptt_shortcut or not self.stop_shortcut or self.ptt_shortcut == self.stop_shortcut or max(len(self.ptt_shortcut), len(self.stop_shortcut)) > 80:
            raise ValueError("Kies twee verschillende geldige sneltoetsen.")
        return self


class VoiceSettingsManager:
    def __init__(self, directory):
        self.path = Path(directory) / "voice-settings.json"

    def load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            settings = VoiceSettings(**{key: value for key, value in raw.items() if key in VoiceSettings.__dataclass_fields__})
            return settings.validate()
        except (OSError, ValueError, TypeError, AttributeError):
            return VoiceSettings()

    def save(self, settings):
        settings.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
        temporary.replace(self.path)


def model_directory(settings):
    return str(Path(settings.models).expanduser().resolve()) if settings.models else str(data_directory() / "models")
