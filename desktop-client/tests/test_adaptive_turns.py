import threading
import time

from jarvis_client.voice.turns import AdaptiveTurn,completed_utterance,IncrementalTranscript


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


def test_incremental_audio_is_not_retranscribed_and_overlap_is_merged():
    import io
    import wave
    frames=[];texts=iter(['Zet een afspraak met','afspraak met Noah morgen','Noah morgen om twee uur.'])
    def recognize(audio,valid):
        with wave.open(io.BytesIO(audio),'rb') as wav:frames.append(wav.getnframes())
        return {'text':next(texts),'seconds':.1}
    stream=IncrementalTranscript(recognize)
    assert stream.request(bytes(256000),lambda:True)['text']=='Zet een afspraak met'
    assert stream.request(bytes(512000),lambda:True)['text']=='Zet een afspraak met Noah morgen'
    result=stream.request(bytes(576000),lambda:True)
    assert result['text']=='Zet een afspraak met Noah morgen om twee uur.'
    assert frames==[128000,136000,40000]
    assert stream.request(bytes(576000),lambda:True)==result and len(frames)==3


def test_incremental_snapshot_does_not_end_turn_while_user_is_speaking():
    seen=[]
    turn=AdaptiveTurn(lambda *_:{'text':'Maak een afspraak met','seconds':.1},lambda:True,normal=.9,thinking=2.5,incremental=True,partial=lambda *args:seen.append(args))
    turn.voiced();turn.probe(bytes(256000),0);wait(turn.pending)
    assert seen and not turn.finished(0) and not turn.finished(.9)
    turn.voiced()
    assert turn.ready() is None
    assert turn.finish(bytes(288000))['text']=='Maak een afspraak met'


def test_incremental_cancelled_chunk_cannot_be_committed():
    active=[True]
    def recognize(*_):active[0]=False;return {'text':'ja','seconds':1}
    stream=IncrementalTranscript(recognize)
    assert stream.request(bytes(256000),lambda:active[0]) is None
    assert stream.end==0 and not stream.text


def test_expired_speculation_cannot_publish_or_block_finish():
    release=threading.Event();now=[0.];partials=[]
    def recognize(*_):release.wait(2);return {'text':'ja'}
    turn=AdaptiveTurn(recognize,lambda:True,normal=.9,thinking=2.5,clock=lambda:now[0],partial=lambda *args:partials.append(args))
    turn.voiced();turn.probe(bytes(960),.9);now[0]=9
    assert turn.finish() is None
    release.set();wait(turn.pending)
    assert not partials and turn.ready() is None
