"""Worker pool and reconnect orchestration. GUI mutations stay on the Qt thread."""
import secrets

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot

from jarvis_client.api import ApiClient, ClientError


class WorkSignals(QObject):
    result = Signal(object)
    error = Signal(object)
    chunk = Signal(object)
    finished = Signal()


class Work(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function, self.signals = function, WorkSignals()

    @Slot()
    def run(self):
        try:
            self.signals.result.emit(self.function(self.signals.chunk.emit))
        except ClientError as error:
            self.signals.error.emit(error)
        except Exception:
            self.signals.error.emit(ClientError("client_error", "De actie kon niet worden uitgevoerd. Controleer instellingen en veilige opslag."))
        finally:
            self.signals.finished.emit()


class Jobs(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(4)
        self.active = set()

    def submit(self, function, result, error, event=None):
        work = Work(function)
        self.active.add(work)
        # Explicit QObject slots below provide queued delivery into the UI thread.
        relay = Delivery(result, error, event, self)
        work.signals.result.connect(relay.result)
        work.signals.error.connect(relay.error)
        work.signals.chunk.connect(relay.stream_chunk)
        work.signals.finished.connect(relay.finished)
        relay.cleanup = lambda: self.active.discard(work)
        self.pool.start(work)


class Delivery(QObject):
    def __init__(self, result, error, event, parent):
        super().__init__(parent)
        self.on_result, self.on_error, self.on_event = result, error, event
        self.cleanup = lambda: None

    @Slot(object)
    def result(self, value):
        self.on_result(value)

    @Slot(object)
    def error(self, value):
        self.on_error(value)

    @Slot(object)
    def stream_chunk(self, value):
        if self.on_event:
            self.on_event(value)

    @Slot()
    def finished(self):
        self.cleanup()
        self.deleteLater()


def backoff(attempt):
    return min(60, 2 ** min(attempt, 6)) + secrets.randbelow(401) / 1000


class ConnectionManager(QObject):
    changed = Signal(str)
    authenticated = Signal(object)
    problem = Signal(object)

    def __init__(self, preferences, vault, jobs, parent=None, factory=ApiClient):
        super().__init__(parent)
        self.preferences, self.vault, self.jobs, self.factory = preferences, vault, jobs, factory
        self.api = None
        self.state, self.attempt, self.generation, self.stopping = "offline", 0, 0, False
        self.busy = False
        self.pinned = False
        self.login_pending = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.check)

    def start(self):
        self.stopping = False
        self.check()

    def check(self):
        if self.stopping or self.busy or self.login_pending:
            return
        self.busy = True
        generation = self.generation
        current = self.api
        candidates = self.preferences.candidates()
        def connect(_):
            failure = None
            for origin in ([current.origin] if current else candidates):
                candidate = current or self.factory(origin, self.vault)
                try:
                    candidate.probe()
                    return candidate, candidate.session()
                except ClientError as error:
                    if error.status == 401:
                        return candidate, None
                    failure = error
                    if candidate is not current:
                        candidate.close()
            # On later checks auto may choose another explicitly configured origin;
            # credentials are always loaded separately for that exact origin.
            if current and self.preferences.connection_mode == "auto" and not self.pinned:
                for origin in candidates:
                    if origin == current.origin:
                        continue
                    candidate = self.factory(origin, self.vault)
                    try:
                        candidate.probe()
                        try:
                            principal = candidate.session()
                        except ClientError as error:
                            if error.status != 401:
                                raise
                            principal = None
                        return candidate, principal
                    except ClientError as error:
                        failure = error
                        candidate.close()
            raise failure or ClientError("network", "Server niet bereikbaar.")

        def connected(value):
            self.busy = False
            candidate, principal = value
            if generation != self.generation or self.stopping:
                if candidate is not self.api:
                    candidate.close()
                return
            if self.api and candidate is not self.api:
                self.api.close()
            self.api = candidate
            self.attempt = 0
            self.state = "online" if principal else "login"
            self.changed.emit(self.state)
            if principal:
                self.authenticated.emit(principal)
            self.timer.start(20000)

        def failed(error):
            self.busy = False
            if generation != self.generation or self.stopping:
                return
            self.state = "offline"
            self.changed.emit(self.state)
            self.problem.emit(error)
            self.timer.start(int(backoff(self.attempt) * 1000))
            self.attempt += 1
        self.jobs.submit(connect, connected, failed)

    def reset(self):
        self.generation += 1
        self.timer.stop()
        if self.api:
            self.api.close()
        self.api = None
        self.state = "offline"
        self.changed.emit(self.state)
        if self.preferences.auto_connect:
            self.timer.start(500)

    def stop(self):
        self.stopping = True
        self.generation += 1
        self.timer.stop()
        if self.api:
            self.api.close()
