from jarvis_client.natural_settings import voice_field_visible,NaturalSettingsPanel
from test_natural_settings import Window


def test_model_visibility_preserves_local_and_supported_premium_controls():
    online={'x-voice-visible':{'premium':True,'models':['eleven_flash_v2_5']}}
    local={'x-voice-visible':{'premium':False}}
    voice={'mode':'premium','tts_provider':'auto','elevenlabs_model':'eleven_flash_v2_5'}
    assert voice_field_visible(online,voice) and not voice_field_visible(local,voice)
    voice['elevenlabs_model']='eleven_v4'
    assert not voice_field_visible(online,voice)
    voice['mode']='offline'
    assert voice_field_visible(local,voice) and not voice_field_visible(online,voice)


def test_elevenlabs_favorite_does_not_overwrite_local_voice(qt):
    window=Window();panel=NaturalSettingsPanel(window)
    panel.document={'settings':{'voice':{'voice':'ronnie','elevenlabs_voice_id':'','speed':1,'volume':.8}}}
    selected=panel.studio_options(('elevenlabs','SyntheticVoice1'))
    assert selected['voice']=='ronnie' and selected['elevenlabs_voice_id']=='SyntheticVoice1' and selected['tts_provider']=='elevenlabs'
    window.close()
