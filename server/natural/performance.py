"""Presets change bounded request settings, never install or select a new model."""
PROFILES={
    "saving":{"context_tokens":2048,"maximum_answer_tokens":512,"timeout_seconds":60},
    "balanced":{"context_tokens":6000,"maximum_answer_tokens":1024,"timeout_seconds":60},
    "latency":{"context_tokens":4000,"maximum_answer_tokens":512,"timeout_seconds":45},
    "quality":{"context_tokens":10000,"maximum_answer_tokens":2048,"timeout_seconds":90},
    "custom":{},
}
