from collections import OrderedDict
import re
import threading
import unicodedata


class InterruptionController:
    def __init__(self):
        self.generation = 0
        self.lock = threading.RLock()

    def cancel(self):
        with self.lock:
            self.generation += 1
            return self.generation

    def valid(self, generation):
        return generation == self.generation


class VoiceActivityDetector:
    """Local energy gate; Whisper's Silero VAD provides a second pass."""
    def __init__(self, sensitivity=0.5, silence=1.2, maximum=60, timeout=6):
        self.threshold = 0.028 - 0.023 * sensitivity
        self.silence, self.maximum, self.timeout = silence, maximum, timeout
        self.elapsed = self.speech = self.quiet = 0.0

    def feed(self, rms, seconds):
        self.elapsed += seconds
        if rms >= self.threshold:
            self.speech += seconds
            self.quiet = 0
        else:
            self.quiet += seconds
        if self.elapsed >= self.maximum or (self.speech >= 0.21 and self.quiet >= self.silence):
            return "finish"
        if self.speech < 0.21 and self.elapsed >= self.timeout:
            return "empty"
        return "continue"


class WakeWordEngine:
    """Explicitly an utterance-level Dutch phrase gate, not a trained wake model."""
    def detect(self, text):
        normalized = "".join(c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c))
        match = re.match(r"^\s*(?:he|hey|hee)\s*[,!.]?\s*j[ae]rvis\b[\s,:.!?\-]*(.*)$", normalized)
        # Preserve the original command (case/accents) using the matched prefix length.
        if not match:
            return False, ""
        original = re.sub(r"^\s*(?:hé|he|hey|hee)\s*[,!.]?\s*j[ae]rvis\b[\s,:.!?\-]*", "", text, count=1, flags=re.IGNORECASE)
        return True, original.strip()


class SentenceBuffer:
    def __init__(self):
        self.pending = ""

    def feed(self, text, final=False):
        self.pending += text
        if len(self.pending) > 18000:
            raise ValueError("Antwoord te lang voor spraak.")
        result = []
        while self.pending:
            # A punctuation token at the current delta boundary may still be a
            # decimal/abbreviation. Wait for whitespace or final completion.
            match = re.search(r"[.!?](?:[\"'”’)]*)\s|\n", self.pending)
            end = match.end() if match else 0
            if not end and len(self.pending) > 400:
                end = self.pending.rfind(" ", 0, 400)
            if not end and final:
                end = len(self.pending)
            if not end:
                break
            segment, self.pending = self.pending[:end].strip(), self.pending[end:]
            if segment:
                # Chat stays literal; speech drops markup delimiters, never runs actions.
                result.append(re.sub(r"[`*_#]", "", segment))
        return result


class AudioCache:
    def __init__(self, maximum=8 * 1024 * 1024):
        self.maximum, self.size, self.items = maximum, 0, OrderedDict()

    def get(self, key):
        value = self.items.get(key)
        if value:
            self.items.move_to_end(key)
        return value

    def put(self, key, value):
        if len(value) > self.maximum:
            return
        previous = self.items.pop(key, b"")
        self.size -= len(previous)
        while self.items and self.size + len(value) > self.maximum:
            _, old = self.items.popitem(last=False)
            self.size -= len(old)
        self.items[key] = value
        self.size += len(value)

    def clear(self):
        self.items.clear()
        self.size = 0
