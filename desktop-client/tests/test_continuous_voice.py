import time
from copy import deepcopy

from PySide6.QtCore import QTimer

from jarvis_client.voice.processing import WakeWordEngine
from test_voice import manager,until
from test_window import window


def options():
    return {"conversations":{"enabled":True,"continuous":True,"auto_listen":True,"wake_word":"Hé JARVIS","inactivity_seconds":90,"maximum_seconds":1800,"automatic_end":True,"ending_phrases":["Bedankt JARVIS","Dat was alles","Tot later"]},
        "voice":{"whisper_model":"whisper-small","processing":"cpu","tts_provider":"piper","voice":"ronnie","speed":1.,"volume":.8,"cache":True},
        "listening":{"maximum_listen_seconds":60,"thinking_pause_ms":2500,"normal_silence_ms":900,"minimum_silence_ms":500,"adaptive":True,"vad_threshold":.015}}


def test_one_wake_word_allows_ten_turns_without_reactivation(qt):
    voice=manager(qt);voice.configure_natural(options());voice.set_authorized(True);voice.set_consent(True)
    assert not voice.recording,'Loading a continuous preference must not activate a microphone'
    texts=[];count=[0]
    def transcribe(*_):
        count[0]+=1
        return {"text":("Hé JARVIS, " if count[0]==1 else "")+"Synthetische beurt "+str(count[0]),"seconds":.01}
    voice.worker.transcribe=transcribe
    def received(text):
        texts.append(text)
        if len(texts)==10:
            voice.toggle_wake(False);return
        voice.begin_response();voice.delta("Een synthetisch antwoord.");voice.finish_response()
    voice.ready_text.connect(received)
    # Skip the real loudspeaker tail delay for these fake, instant audio devices.
    voice.playback_finished.connect(lambda:QTimer.singleShot(0,voice._auto_listen))
    voice.toggle_wake(True)
    until(qt,lambda:len(texts)==10,seconds=5)
    assert count[0]==10 and all("JARVIS" not in item for item in texts)
    assert not voice.recording and not voice.wake_enabled
    voice.close()


def test_ending_and_idle_timeout_stop_continuation_but_thanks_with_question_does_not(qt):
    voice=manager(qt);voice.configure_natural(options());voice.set_authorized(True);voice.set_consent(True);voice.activate_session()
    assert voice.farewell("Bedankt JARVIS!") and not voice.farewell("Bedankt JARVIS, vertel me nog iets.")
    voice.last_activity=time.monotonic()-91
    ended=[];voice.session_ended.connect(ended.append);voice._auto_listen()
    assert ended==["time-out"] and not voice.session_active and not voice.recording
    voice.close()


def test_configured_wake_phrase_and_effective_audio_settings(qt):
    assert WakeWordEngine().detect("Oké Atlas, vertel over België.","Oké Atlas")== (True,"vertel over België.")
    assert WakeWordEngine().detect("Ik las over Atlas","Oké Atlas")== (False,"")
    voice=manager(qt);config=options();config["voice"]["speed"]=1.2
    config["listening"]["thinking_pause_ms"]=3000
    voice.configure_natural(config)
    effective=voice.effective_settings()
    assert effective.speed==1.2 and effective.silence_seconds==3
    assert voice.settings.speed==1 and not voice.consent and not voice.recording
    voice.close()


def test_native_session_uses_epoch_and_rejects_late_callbacks(qt,tmp_path,vault):
    app=window(tmp_path,vault);app.voice.configure_natural(options());app.principal={"permissions":["chat:write"]}
    calls=[];sent=[];app.call=lambda method,path,body,done,failure=None:calls.append((method,path,deepcopy(body),done))
    app.send_voice_text=sent.append
    controller=app.voice_session;controller.submit("Synthetisch")
    assert calls[-1][1].endswith("/start") and calls[-1][2]=={"takeover":False}
    session={"conversation_id":"synthetic-conversation","device_id":"synthetic-device","epoch":7,"revision":1,"state":"ACTIVATING"}
    calls[-1][3](session)
    assert calls[-1][2]=={"event":"listening","epoch":7}
    calls[-1][3]({**session,"state":"LISTENING","revision":2})
    assert calls[-1][0]=="GET" and calls[-1][1].endswith("/state")
    calls[-1][3]({**session,"state":"LISTENING","revision":2})
    assert calls[-1][2]=={"event":"processing","epoch":7}
    callback=calls[-1][3];controller.clear();callback({**session,"state":"PROCESSING","revision":3})
    assert not sent and controller.current is None
    app.closing=True;app.voice_panel.close_voice();app.tray.hide();app.close()
