import threading
import time

from jarvis_client.voice.turns import AdaptiveTurn,completed_utterance


def wait(future):
    return future.result(timeout=2)


def test_complete_question_can_finish_before_maximum_but_thinking_waits():
    turn=AdaptiveTurn(lambda *_:{"text":"Hoe heet je?"},lambda:True,normal=.9,thinking=2.5)
    turn.voiced();turn.probe(b"\0\0"*480,.9);wait(turn.pending)
    assert not turn.finished(.5) and turn.finished(.9)
    assert turn.finish()["text"]=="Hoe heet je?"
    assert not completed_utterance("Maak vrijdag een afspraak, ehm")
    assert not completed_utterance("Maak vrijdag een afspraak")
    assert completed_utterance("Maak vrijdag om half vier een afspraak")


def test_resumed_speech_invalidates_old_snapshot_without_stopping_capture():
    entered=threading.Event();release=threading.Event();partials=[]
    def recognize(*_):
        entered.set();release.wait(2);return {"text":"Een oud fragment"}
    turn=AdaptiveTurn(recognize,lambda:True,normal=.9,thinking=2.5,partial=lambda *args:partials.append(args))
    turn.voiced();turn.probe(b"\0\0"*480,.9);assert entered.wait(1)
    turn.voiced();release.set();wait(turn.pending)
    assert turn.ready() is None and turn.finish() is None and not partials
    assert not turn.finished(.9) and turn.finished(2.5)


def test_failed_partial_recognition_falls_back_without_retry_loop():
    calls=[]
    def recognize(*_):calls.append(1);raise RuntimeError("synthetic")
    turn=AdaptiveTurn(recognize,lambda:True,normal=.9,thinking=2.5)
    turn.voiced();turn.probe(b"\0\0"*480,.9);wait(turn.pending)
    turn.probe(b"\0\0"*480,1.2)
    assert calls==[1] and turn.finish() is None


def test_cancellation_does_not_wait_for_or_publish_late_transcript():
    release=threading.Event();active=[True];partials=[]
    def recognize(*_):release.wait(2);return {"text":"Late tekst"}
    turn=AdaptiveTurn(recognize,lambda:active[0],normal=.9,thinking=2.5,partial=lambda *args:partials.append(args))
    turn.voiced();turn.probe(b"\0\0"*480,.9);active[0]=False
    start=time.monotonic();assert turn.finish() is None and time.monotonic()-start<.2
    release.set();wait(turn.pending);assert not partials
