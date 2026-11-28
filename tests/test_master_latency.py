import math

from server.natural.diagnostics import distributions
from tests.test_natural_settings_memory import natural as natural


def test_tails_count_real_samples_and_separate_progress():
    rows=[{'event':'native_content_audio_ms','metric':n} for n in range(1,101)]
    rows += [{'event':'native_progress_audio_ms','metric':500},{'event':'native_content_audio_ms','metric':math.nan}]
    data=distributions(rows)
    assert data['native_content_audio_ms']=={'count':100,'p50':50,'p95':95,'p99':99}
    assert data['native_progress_audio_ms']['p50']==500
    assert distributions([])=={}


def test_content_and_progress_metrics_have_distinct_authenticated_distributions(natural):
    app,c=natural
    for name,value in [('native_progress_audio_ms',400.),('native_content_audio_ms',2500.),('native_final_audio_ms',4200.)]:
        assert c.post('/api/v1/natural/diagnostics/metrics',json={'items':[{'event':name,'value':value}]}).status_code==200
    data=c.get('/api/v1/natural/diagnostics').json()
    assert data['distributions']['native_content_audio_ms']['p50']==2500
    assert data['distributions']['native_progress_audio_ms']['p50']==400
