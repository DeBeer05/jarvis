"""Same-user, profile-scoped activation of the existing Qt window."""
import hashlib
from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QLocalServer,QLocalSocket


def channel_name(directory):
    return 'jarvis-desktop-'+hashlib.sha256(str(directory.resolve()).casefold().encode()).hexdigest()[:32]


def show_existing(directory):
    socket=QLocalSocket();socket.connectToServer(channel_name(directory))
    if not socket.waitForConnected(700):return False
    socket.write(b'show\n');socket.flush()
    ready=socket.bytesAvailable()>0 or socket.waitForReadyRead(700)
    ok=ready and bytes(socket.readAll())==b'ok\n'
    socket.disconnectFromServer()
    return bool(ok)


class WindowActivation:
    def __init__(self,directory,restore):
        self.server=QLocalServer();self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.restore=restore;self.clients=set()
        name=channel_name(directory)
        # Caller owns the profile lock: a previous crashed process may leave a socket.
        QLocalServer.removeServer(name)
        self.server.newConnection.connect(self.accept)
        if not self.server.listen(name):raise OSError('Window activation unavailable')

    def accept(self):
        while self.server.hasPendingConnections():
            socket=self.server.nextPendingConnection();self.clients.add(socket)
            buffer=bytearray()
            def receive(socket=socket,buffer=buffer):
                buffer.extend(bytes(socket.readAll()))
                if len(buffer)>64:socket.abort();return
                if b'\n' not in buffer:return
                if bytes(buffer)==b'show\n':self.restore();socket.write(b'ok\n');socket.flush()
                socket.disconnectFromServer()
            def clear(socket=socket):self.clients.discard(socket);socket.deleteLater()
            socket.readyRead.connect(receive);socket.disconnected.connect(clear)
            timer=QTimer(socket);timer.setSingleShot(True);timer.timeout.connect(socket.abort);timer.start(1500)
            if socket.bytesAvailable():receive()

    def close(self):
        for socket in list(self.clients):socket.abort()
        self.server.close()
