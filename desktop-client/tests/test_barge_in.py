import threading

import numpy as np
import pytest

from jarvis_client.voice.echo import EchoReference,resembles_output
from jarvis_client.voice.manager import VoiceConversationManager
from jarvis_client.voice.settings import VoiceSettings
from test_continuous_voice import options
from test_voice import FakeWorker,until


def test_reference_suppresses_delayed_echo_but_keeps_unrelated_speech():
    rng=np.random.default_rng(42);reference=rng.normal(0,3000,16000).astype(np.int16)
    gate=EchoReference();gate.feed(reference.tobytes(),16000)
    echo=(reference[8000:8480]*.4).astype(np.int16)
    cleaned=gate.filter(echo)
    assert np.sqrt(np.mean(cleaned.astype(float)**2))<np.sqrt(np.mean(echo.astype(float)**2))*.15
    other=rng.normal(0,2000,480).astype(np.int16)
    assert np.array_equal(gate.filter(other),other)
    for _ in range(150):gate.feed(reference[:320].tobytes(),16000)
    assert len(gate.blocks)<=100
    gate.clear();assert not gate.blocks and np.array_equal(gate.filter(other),other)


@pytest.mark.parametrize("text",["Je hebt morgen een afspraak","Ja","Zeg ja om te bevestigen"])
def test_own_tts_cannot_become_a_new_command_or_approval(text):
    assert resembles_output(text,"Je hebt morgen een afspraak. Zeg ja om te bevestigen.")
    assert not resembles_output("Wacht even welke afspraak bedoel je?",text)


class DuplexInput:
    def __init__(self):self.stopped=threading.Event();self.entered=threading.Event();self.release=threading.Event()
    def prepare(self):self.stopped.clear();self.release.clear()
    def stop(self,discard=False):self.stopped.set();self.release.set()
    def capture(self,settings,**kwargs):
        self.entered.set();self.release.wait(2)
        if self.stopped.is_set():return b""
        for _ in range(5):kwargs["activity"](.1,True)
        return b"synthetic"


class DuplexOutput:
    def __init__(self):self.stopped=threading.Event();self.paused=threading.Event();self.started=threading.Event()
    def pause(self):self.paused.set()
    def resume(self):self.paused.clear()
    def stop(self):self.stopped.set()
    def play(self,data,settings,valid,on_started):
        self.stopped.clear();on_started();self.started.set()
        while valid() and not self.stopped.wait(.005):pass


def make(qt,text):
    input=DuplexInput();output=DuplexOutput();worker=FakeWorker()
    worker.transcribe=lambda *_:{"text":text,"seconds":.01}
    voice=VoiceConversationManager(VoiceSettings(),worker=worker,audio_input=input,audio_output=output)
    config=options();config["listening"].update(barge_in=True,barge_in_sensitivity=.7,echo_suppression=True)
    voice.configure_natural(config);voice.set_authorized(True);voice.set_consent(True);voice.activate_session()
    voice.voice_next=True;voice.begin_response();voice.delta("Je hebt morgen een afspraak. ")
    until(qt,lambda:input.entered.is_set())
    return voice,input,output


def test_verified_interruption_stops_old_output_keeps_context_and_accepts_next_utterance(qt):
    voice,input,output=make(qt,"Wacht even, welke afspraak bedoel je?")
    messages=[];interruptions=[];voice.ready_text.connect(messages.append);voice.interrupted.connect(lambda:interruptions.append(True))
    old=voice.interruptions.generation;input.release.set()
    until(qt,lambda:bool(messages))
    assert output.stopped.is_set() and not voice.interruptions.valid(old)
    assert interruptions==[True] and voice.session_active and voice.voice_next
    assert messages==["Wacht even, welke afspraak bedoel je?"]
    voice.close()


def test_echo_and_stop_during_capture_cannot_submit_late_text(qt):
    voice,input,output=make(qt,"Je hebt morgen een afspraak")
    messages=[];voice.ready_text.connect(messages.append);input.release.set()
    until(qt,lambda:voice.measurements.get("rejected_interruptions")==1)
    assert not messages and voice.responding and not output.paused.is_set()
    voice.stop();old=voice.interruptions.generation-1
    voice._delivered((old,"barge_captured",{"text":"ja"}))
    assert not messages and not voice.recording and not voice.session_active
    voice.close()


def test_barge_in_disabled_never_opens_a_second_microphone(qt):
    voice,input,output=make(qt,"Stop")
    voice.stop();input.entered.clear();voice.options["listening"]["barge_in"]=False
    voice.voice_next=True;voice.begin_response();voice.delta("Nog een antwoord. ")
    until(qt,lambda:output.started.is_set())
    qt.processEvents();assert not input.entered.is_set()
    voice.close()
