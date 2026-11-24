"""Standard-library supervision for the existing private voice worker protocol."""
import json
import logging
import os
import queue
import subprocess
import sys
import threading
import time

logger=logging.getLogger("jarvis.voice")


class OwnedVoicePipe:
    def __init__(self,command=None):
        self.command=command;self.process=None;self.lock=threading.Lock();self.state_lock=threading.RLock()
        self.epoch=0;self.cleanup_threads=[];self.inflight=threading.Event()

    @property
    def busy(self):return self.inflight.is_set() or any(thread.is_alive() for thread in self.cleanup_threads)

    def resolve_command(self):
        if self.command:return self.command() if callable(self.command) else self.command
        raise RuntimeError("Spraakruntime ontbreekt.")

    def cancel_pending(self):
        if self.inflight.is_set():self.cancel()

    def cancel(self):
        with self.state_lock:
            self.epoch+=1;process,self.process=self.process,None
        if process:
            thread=threading.Thread(target=self._reap,args=(process,),daemon=True)
            self.cleanup_threads=[item for item in self.cleanup_threads if item.is_alive()]+[thread];thread.start()

    @staticmethod
    def _reap(process):
        try:
            if sys.platform=="win32" and process.poll() is None:
                result=subprocess.run([os.path.join(os.environ["SystemRoot"],"System32","taskkill.exe"),"/PID",str(process.pid),"/T","/F"],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=5,check=False)
                logger.info("Owned speech helper stopped status=%d",result.returncode)
            elif process.poll() is None:process.terminate()
            process.wait(timeout=2)
        except (OSError,subprocess.TimeoutExpired):
            if process.poll() is None:process.kill()
        finally:
            for stream in (process.stdin,process.stdout):
                try:stream.close()
                except (OSError,ValueError,AttributeError):pass

    @staticmethod
    def _stderr(stream):
        warned=False
        try:
            while stream.read(4096):
                if not warned:logger.warning("Voice helper emitted native diagnostics; private contents omitted");warned=True
        finally:stream.close()

    def exchange(self,request,*,valid=lambda:True,timeout=100):
        encoded=json.dumps(request,ensure_ascii=True).encode("ascii")+b"\n"
        if len(encoded)>24*1024*1024:raise ValueError("voice_request_too_large")
        with self.lock:
            if not valid():raise RuntimeError("Spraakopdracht geannuleerd.")
            self.inflight.set()
            try:
                with self.state_lock:
                    if self.process is None or self.process.poll() is not None:
                        self.process=subprocess.Popen(self.resolve_command(),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                        threading.Thread(target=self._stderr,args=(self.process.stderr,),daemon=True).start()
                    process,epoch=self.process,self.epoch
                result:queue.Queue[dict]=queue.Queue(maxsize=1)
                def transfer():
                    try:
                        if process.stdin is None or process.stdout is None:raise ValueError("voice_pipes_unavailable")
                        process.stdin.write(encoded);process.stdin.flush()
                        line=process.stdout.readline(24*1024*1024)
                        if not line.endswith(b"\n"):raise ValueError("voice_protocol")
                        value=json.loads(line)
                        if not isinstance(value,dict):raise ValueError("voice_protocol")
                        result.put(value)
                    except Exception:result.put({"ok":False,"code":"voice_failed"})
                threading.Thread(target=transfer,daemon=True).start();deadline=time.monotonic()+timeout
                while True:
                    if not valid() or epoch!=self.epoch:
                        self.cancel();raise RuntimeError("Spraakopdracht geannuleerd.")
                    try:
                        response=result.get(timeout=.05)
                        if not valid() or epoch!=self.epoch:raise RuntimeError("Spraakopdracht geannuleerd.")
                        return response
                    except queue.Empty:
                        if time.monotonic()>=deadline:
                            self.cancel();raise TimeoutError("voice_timeout")
            finally:self.inflight.clear()
