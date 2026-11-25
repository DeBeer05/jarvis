"""Synthetic in-memory Piper -> Whisper benchmark. No mic, speaker or server."""
import argparse
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "desktop-client"))
from jarvis_client.voice.processing import WakeWordEngine
from jarvis_client.voice.settings import VoiceSettings
from jarvis_client.voice.worker import InferenceWorker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turns", type=int, default=12, choices=range(1, 31))
    parser.add_argument("--output", type=Path, default=Path(".local/phase5-engine-benchmark.json"))
    parser.add_argument("--helper", type=Path)
    args = parser.parse_args()
    worker = InferenceWorker(command=[str(args.helper.resolve())] if args.helper else None)
    records = []
    texts = ["Hallo, ik ben Jarvis. Hoe kan ik je vandaag helpen?", "Hé Jarvis, hoeveel is zeven plus vijf?",
             "Mijn naam is Eva. Kun je onthouden dat ik morgen om negen uur wil beginnen?"]
    started = time.perf_counter()
    try:
        for index in range(args.turns):
            text = texts[index % len(texts)]
            before = time.perf_counter()
            audio, tts = worker.synthesize(text, VoiceSettings(), lambda: True)
            with wave.open(io.BytesIO(audio), "rb") as stream:
                duration = stream.getnframes() / stream.getframerate()
            result = worker.transcribe(audio, VoiceSettings(), lambda: True)
            record = {"turn": index + 1, "input": text, "transcript": result["text"], "audio_seconds": round(duration, 3),
                      "tts_seconds": round(tts["seconds"], 3), "stt_seconds": round(result["seconds"], 3),
                      "device": result["device"], "cpu_fallback": result["cpu_fallback"],
                      "roundtrip_seconds": round(time.perf_counter() - before, 3), "runtime_stats": result.get("runtime_stats", {})}
            if index % 3 == 1:
                record["wake_detected"] = WakeWordEngine().detect(result["text"])[0]
            records.append(record)
            print(json.dumps(record, ensure_ascii=True), flush=True)
        elapsed = time.perf_counter() - started
        try:
            gpu = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=10, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            gpu_snapshot = gpu.stdout.strip() if gpu.returncode == 0 else "unavailable"
        except (OSError, subprocess.TimeoutExpired):
            gpu_snapshot = "unavailable"
        report = {"records": records, "wall_seconds": round(elapsed, 3),
                  "median_stt_seconds": statistics.median(item["stt_seconds"] for item in records),
                  "median_tts_seconds": statistics.median(item["tts_seconds"] for item in records),
                  "cpu_machine_percent": round(records[-1]["runtime_stats"].get("cpu_seconds", 0) / elapsed / (os.cpu_count() or 1) * 100, 2),
                  "gpu_snapshot_util_percent_used_total_mib": gpu_snapshot,
                  "physical_audio_tested": False, "live_ai_tested": False}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    finally:
        worker.cancel()
        deadline = time.monotonic() + 8
        while worker.busy and time.monotonic() < deadline:
            time.sleep(.05)


if __name__ == "__main__":
    main()
