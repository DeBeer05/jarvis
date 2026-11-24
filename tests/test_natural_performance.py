from tests.test_natural_context import build,client,patch


def test_performance_presets_change_real_ai_policy_and_preserve_explicit_edits(settings):
    app,providers=build(settings)
    with client(app) as c:
        patch(c,"ai",{"performance":"saving","maximum_answer_tokens":768})
        document=c.get("/api/v1/natural/settings").json()
        assert document["settings"]["ai"]["context_tokens"]==2048
        assert document["settings"]["ai"]["maximum_answer_tokens"]==768
        from server.ai.policy import RequestPolicy
        policy=RequestPolicy.from_document(document)
        assert policy.maximum_answer_tokens==768
        patch(c,"ai",{"performance":"quality"})
        ai=c.get("/api/v1/natural/settings").json()["settings"]["ai"]
        assert ai["context_tokens"]==10000 and ai["maximum_answer_tokens"]==2048 and ai["timeout_seconds"]==90
        patch(c,"ai",{"performance":"custom","context_tokens":3000})
        assert c.get("/api/v1/natural/settings").json()["settings"]["ai"]["context_tokens"]==3000
