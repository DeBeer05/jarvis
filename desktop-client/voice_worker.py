# SPDX-License-Identifier: GPL-3.0-or-later
"""Private pipe worker: stdout is protocol only, no audio/transcript logging."""
import json
import sys
import time
from voice_runtime.engines import Runtime


def statistics():
    result = {"cpu_seconds": time.process_time()}
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("page_faults", wintypes.DWORD)] + [(key, ctypes.c_size_t) for key in (
                "peak_ram_bytes", "ram_bytes", "quota_peak_paged", "quota_paged", "quota_peak_nonpaged", "quota_nonpaged", "pagefile", "peak_pagefile", "private_bytes")]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            result.update({"ram_bytes": counters.ram_bytes, "peak_ram_bytes": counters.peak_ram_bytes})
    return result


def main():
    runtime = Runtime()
    while line := sys.stdin.buffer.readline(24 * 1024 * 1024):
        try:
            if not line.endswith(b"\n"):
                break
            result = runtime.dispatch(json.loads(line))
            result["runtime_stats"] = statistics()
            response = {"ok": True, "result": result}
        except ValueError as error:
            code = str(error)
            response = {"ok": False, "code": code if code in {"stt_model_missing", "tts_model_missing", "tts_provider_unavailable", "invalid_text", "invalid_settings", "audio_too_long"} else "voice_failed"}
        except Exception:
            # Native/model errors may contain private text or paths: never echo.
            response = {"ok": False, "code": "voice_failed"}
        sys.stdout.write(json.dumps(response, ensure_ascii=True) + "\n")
        sys.stdout.flush()
        # Private protocol payloads are not an audio/transcript cache.
        result=response=None
        line=b""


if __name__ == "__main__":
    main()
