"""Native audio lease over the existing authenticated API; no transport credentials."""
from PySide6.QtCore import QObject,QTimer

BASE="/api/v1/natural/conversations"


class ConversationSession(QObject):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.current=None;self.serial=0;self.pending=None;self.busy=False;self.heartbeat_busy=False
        self.timer=QTimer(self);self.timer.setInterval(20000);self.timer.timeout.connect(self.heartbeat)

    def enabled(self):
        options=self.window.voice.options
        return bool(options and options["conversations"]["enabled"])

    def clear(self):
        self.serial+=1;self.current=None;self.pending=None;self.busy=False;self.heartbeat_busy=False;self.timer.stop()

    def request(self,path,body,done,*,method="POST"):
        serial=self.serial
        def success(value):
            if serial==self.serial:done(value)
        def failure(error):
            if serial!=self.serial:return
            self.clear();self.window.voice.stop()
            self.window.voice.problem.emit("Spraakgesprek niet beschikbaar. Selecteer het gesprek in Gesprekken en kies ‘Gesprek hier overnemen’ als het op een ander apparaat actief is. Er is geen opdracht opnieuw verstuurd.")
        self.window.call(method,BASE+path,body,success,failure)

    def submit(self,text):
        self.pending=text
        if self.busy:return
        self.busy=True
        if not self.current or self.current["conversation_id"]!=self.window.conversation:self.claim(False,self.processing)
        else:self.processing(self.current)

    def claim(self,takeover,done):
        body={"takeover":takeover}
        if self.window.conversation:body["conversation_id"]=self.window.conversation
        def claimed(session):
            self.current=session;self.window.conversation=session["conversation_id"];self.timer.start()
            self.send_event("listening",done)
        self.request("/start",body,claimed)

    def send_event(self,name,done=None):
        if not self.current:return
        session=dict(self.current)
        def received(value):
            if self.current and self.current["conversation_id"]==value["conversation_id"] and (value["epoch"],value.get("revision",0))<(self.current["epoch"],self.current.get("revision",0)):
                if done:done(self.current)
                return
            self.current=value
            if done:done(value)
        self.request("/"+session["conversation_id"]+"/events",{"event":name,"epoch":session["epoch"]},received)

    def processing(self,_):
        if not self.current:return
        expected=dict(self.current)
        def checked(state):
            if state["state"] in ("STANDBY","RECONNECTING","ENDING","ERROR"):
                self.current=None;self.claim(False,self.processing);return
            if state["epoch"]!=expected["epoch"] or state["device_id"]!=expected.get("device_id",state["device_id"]):
                self.clear();self.window.voice.stop();self.window.voice.problem.emit("Dit gesprek is overgenomen. Kies expliciet Gesprek hier overnemen.");return
            self.current=state
            if state["state"] in ("PROCESSING","THINKING","ASSISTANT_SPEAKING","EXECUTING_ACTION"):
                self.send_event("interrupted",self.ready_for_processing)
            else:self.ready_for_processing(state)
        self.request("/"+expected["conversation_id"]+"/state",None,checked,method="GET")

    def ready_for_processing(self,_):
        def ready(session):
            text,self.pending=self.pending,None;self.busy=False
            if text:
                self.window.voice.activate_session();self.window.voice.voice_next=True
                self.window.send_voice_text(text)
        self.send_event("processing",ready)

    def listened(self):
        if self.current and not self.busy:self.send_event("listening")

    def heartbeat(self):
        if not self.current or self.heartbeat_busy:return
        self.heartbeat_busy=True
        def done(value):self.current=value;self.heartbeat_busy=False
        self.send_event("heartbeat",done)

    def end(self,reason="afgesloten"):
        if self.current and self.window.principal and not self.window.closing:
            session=dict(self.current)
            self.window.call("POST",BASE+"/"+session["conversation_id"]+"/events",{"event":"ending","epoch":session["epoch"]},lambda _:None,lambda _:None)
        self.clear()

    def takeover(self):
        if not self.window.principal or not self.window.voice.consent:
            self.window.show_notice("Log in en geef lokaal microfoontoestemming voordat je een gesprek overneemt.");return
        if self.window.running:return
        self.clear();self.busy=True
        def ready(_):
            self.busy=False;self.window.voice.activate_session();self.window.voice.armed=True;self.window.voice.start_recording(automatic=True)
        self.claim(True,ready)
