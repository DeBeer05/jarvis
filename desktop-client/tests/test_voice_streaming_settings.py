from test_voice import manager,until
from test_continuous_voice import options


def test_deferred_voice_waits_for_success_and_settings_changes_apply_next_turn(qt):
    voice=manager(qt);config=options();config["voice"]["streaming"]=False
    voice.configure_natural(config);voice.voice_next=True;voice.begin_response()
    voice.delta("Een compleet antwoord. ")
    assert voice.pending.empty() and not voice.output.played
    config["voice"]["streaming"]=True;voice.configure_natural(config)
    voice.finish_response(True)
    until(qt,lambda:bool(voice.output.played))
    assert voice.output.played==[b"Een compleet antwoord."]
    voice.close()


def test_failed_deferred_response_is_never_spoken(qt):
    voice=manager(qt);config=options();config["voice"]["streaming"]=False
    voice.configure_natural(config);voice.voice_next=True;voice.begin_response()
    voice.delta("Een onbevestigd deelantwoord. ");voice.finish_response(False)
    assert not voice.output.played
    voice.close()
