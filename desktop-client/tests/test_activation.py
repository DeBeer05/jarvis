import subprocess
import sys
from pathlib import Path
import time
from PySide6.QtNetwork import QLocalSocket
from jarvis_client.activation import WindowActivation,show_existing,channel_name


def test_second_launch_restores_same_profile_window(qt,tmp_path):
    called=[];listener=WindowActivation(tmp_path,lambda:called.append(True))
    try:
        code="import sys;sys.path.insert(0,sys.argv[1]);from pathlib import Path;from PySide6.QtCore import QCoreApplication;from jarvis_client.activation import show_existing;app=QCoreApplication([]);raise SystemExit(0 if show_existing(Path(sys.argv[2])) else 1)"
        process=subprocess.Popen([sys.executable,"-c",code,str(Path(__file__).resolve().parents[1]),str(tmp_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        end=time.monotonic()+4
        while process.poll() is None and time.monotonic()<end:qt.processEvents();time.sleep(.005)
        stdout,stderr=process.communicate(timeout=1)
        assert process.returncode==0 and called==[True], (stdout,stderr,called)
        assert not show_existing(tmp_path/'another-profile')
    finally:listener.close()


def test_activation_rejects_arbitrary_commands(qt,tmp_path):
    called=[];listener=WindowActivation(tmp_path,lambda:called.append(True));client=QLocalSocket()
    try:
        client.connectToServer(channel_name(tmp_path));assert client.waitForConnected(100)
        client.write(b'execute something\n');client.flush()
        for _ in range(10):qt.processEvents()
        assert not called
    finally:client.abort();listener.close()
