"""Bounded numeric telemetry. No prompts, raw audio, paths or provider errors."""
import os
import threading
import time
import shutil
import subprocess
from pathlib import Path

from server.natural.capabilities import voice_capabilities

EVENTS=frozenset({"ai_first_token_ms","response_total_ms","stt_ms","tts_ms","native_first_audio_ms",
                  "native_stt_ms","native_total_ms","context_ms","intent_ms","tool_execution_ms","source_fetch_ms","context_tokens","interruption","rejected_interruption","wake_miss","error"})
CODES=frozenset({"timeout","unavailable","cancelled","permission_denied","internal_error","invalid_audio","invalid_parameters"})


def resident_bytes(pid):
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD),
                *[(key,ctypes.c_size_t) for key in ("PeakWorkingSetSize","WorkingSetSize","QuotaPeakPagedPoolUsage","QuotaPagedPoolUsage","QuotaPeakNonPagedPoolUsage","QuotaNonPagedPoolUsage","PagefileUsage","PeakPagefileUsage")]]
        windows_library=getattr(ctypes,"WinDLL")
        kernel=windows_library("kernel32",use_last_error=True);api=windows_library("psapi",use_last_error=True)
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        api.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        handle=kernel.OpenProcess(0x1000|0x10,False,pid)
        if not handle:return None
        try:
            counters=Counters();counters.cb=ctypes.sizeof(counters)
            return int(counters.WorkingSetSize) if api.GetProcessMemoryInfo(handle,ctypes.byref(counters),counters.cb) else None
        finally:kernel.CloseHandle(handle)
    try:return int((Path("/proc")/str(pid)/"statm").read_text().split()[1])*getattr(os,"sysconf")("SC_PAGE_SIZE")
    except (OSError,ValueError,IndexError):return None


class DiagnosticsManager:
    def __init__(self,store,settings):
        self.store,self.settings=store,settings;self.lock=threading.Lock();self.previous=None
        self.gpu_lock=threading.Lock();self.gpu_at=-100.;self.gpu_sample=None

    def gpu(self):
        with self.gpu_lock:
            if time.monotonic()-self.gpu_at<30:return self.gpu_sample
            self.gpu_at=time.monotonic();self.gpu_sample=None
            executable=shutil.which("nvidia-smi")
            if not executable:return None
            try:
                result=subprocess.run([executable,"--query-gpu=utilization.gpu,memory.used","--format=csv,noheader,nounits"],
                    capture_output=True,text=True,check=True,timeout=2,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                if len(result.stdout)>4096:return None
                values=[]
                for row in result.stdout.strip().splitlines()[:4]:
                    percent,memory=map(float,row.split(","))
                    if not 0<=percent<=100 or not 0<=memory<=1_000_000:return None
                    values.append({"utilization_percent":percent,"memory_used_mib":memory})
                self.gpu_sample=values or None
            except (OSError,ValueError,subprocess.SubprocessError):pass
            return self.gpu_sample

    def record(self,principal,event,value=None,code=None):
        if event not in EVENTS or code is not None and code not in CODES:raise ValueError("Onbekende diagnostiekcode")
        if value is not None and (type(value) not in (int,float) or not 0<=value<=3_600_000):raise ValueError("Ongeldige meetwaarde")
        config=self.settings.get(principal)["settings"]
        if not config["diagnostics"]["enabled"]:return
        if (event.endswith("_ms") or event=="context_tokens") and not config["diagnostics"]["latency"]:return
        with self.store.transaction(principal,write=True) as (db,user):
            now=self.store.clock()
            db.execute("INSERT INTO natural_diagnostics(user_id,device_id,at,event,metric,code) VALUES (?,?,?,?,?,?)",(user,principal.device_id,now,event,value,code))
            db.execute("DELETE FROM natural_diagnostics WHERE user_id=? AND (at<? OR id IN (SELECT id FROM natural_diagnostics WHERE user_id=? ORDER BY id DESC LIMIT -1 OFFSET ?))",(user,now-config["privacy"]["diagnostic_days"]*86400,user,config["diagnostics"]["maximum_events"]))

    def resources(self,helper=None):
        now=time.monotonic();cpu=time.process_time()
        with self.lock:
            previous=self.previous;self.previous=(now,cpu)
        load=None if previous is None else round(max(0,(cpu-previous[1])/max(.001,now-previous[0])*100),2)
        gpu=self.gpu()
        return {"scope":"server_process","cpu_one_core_percent":load,"resident_bytes":resident_bytes(os.getpid()),
                "voice_helper_resident_bytes":resident_bytes(helper) if helper else None,"gpu_percent":gpu[0]["utilization_percent"] if gpu else None,
                "gpu_devices":gpu,"gpu_status":"available_system_wide" if gpu else "not_measured"}

    def response(self,run):
        for event,value in run.timings.items():
            if event in EVENTS:self.record(run.principal,event,value)
        self.record(run.principal,"response_total_ms",(time.perf_counter()-run.started_at)*1000)
        if run.first_token_seconds is not None:self.record(run.principal,"ai_first_token_ms",run.first_token_seconds*1000)
        if run.context_metrics.get("estimated_tokens") is not None:self.record(run.principal,"context_tokens",run.context_metrics["estimated_tokens"])
        if run.status=="error":self.record(run.principal,"error",code=run.error["code"] if run.error and run.error["code"] in CODES else "unavailable")

    def snapshot(self,principal,*,helper=None,inference_busy=False):
        config=self.settings.get(principal)["settings"];now=self.store.clock()
        with self.store.transaction(principal,write=True) as (db,user):
            db.execute("DELETE FROM natural_diagnostics WHERE user_id=? AND at<?",(user,now-config["privacy"]["diagnostic_days"]*86400))
            events=[dict(row) for row in db.execute("SELECT at,event,metric,code FROM natural_diagnostics WHERE user_id=? ORDER BY id DESC LIMIT ?",(user,config["diagnostics"]["maximum_events"])).fetchall()]
            sessions=[dict(row) for row in db.execute("SELECT conversation_id,device_id,state,epoch,lease_until FROM natural_sessions WHERE user_id=? ORDER BY activity DESC LIMIT 10",(user,)).fetchall()]
            counts={row["status"]:row["count"] for row in db.execute("SELECT status,count(*) AS count FROM natural_memories WHERE user_id=? GROUP BY status",(user,)).fetchall()}
            latest=db.execute("SELECT t.provider FROM chat_turns t JOIN natural_conversation_owners o ON o.conversation_id=t.conversation_id WHERE o.user_id=? AND t.provider IS NOT NULL ORDER BY t.created_at DESC LIMIT 1",(user,)).fetchone()
        latency={event:next((row["metric"] for row in events if row["event"]==event),None) for event in EVENTS if event.endswith("_ms") or event=="context_tokens"}
        capabilities=voice_capabilities()
        return {"schema_version":1,"sampled_at":now,"enabled":config["diagnostics"]["enabled"],"server":"online","database":"read_write_ok",
                "active_provider":latest["provider"] if latest and latest["provider"] in ("gemini","groq","ollama","oracle","local","jarvis") else None,
                "voice":{"capabilities":capabilities,"inference_busy":inference_busy},"websocket":"not_configured","microphone":"device_local",
                "sessions":sessions,"memory_counts":counts,"latency":latency,"events":events,
                "resources":self.resources(helper) if config["diagnostics"]["enabled"] and config["diagnostics"]["resources"] else None,
                "contains_conversation_content":False}
