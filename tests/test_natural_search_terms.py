from tests.test_natural_settings_memory import natural as natural
from tests.test_natural_context import patch
from server.natural.search_terms import expand


def test_related_vocabulary_is_opt_in_and_never_retrieves_deleted_or_sensitive_memory(natural):
    app,c=natural
    plain=c.post("/api/v1/natural/memory",json={"content":"Ik plan afspraken liever na tien uur"}).json()
    c.post("/api/v1/natural/memory",json={"content":"Gevoelige afsprakenvoorkeur","sensitivity":"sensitive","consent_sensitive":True})
    principal=app.state.security.store.authenticate(c.cookies.get("jarvis_access"));manager=app.state.natural.memory
    assert not manager.retrieve(principal,"kalender")
    patch(c,"memory",{"semantic_search":True})
    assert [row["id"] for row in manager.retrieve(principal,"kalender")]==[plain["id"]]
    c.delete("/api/v1/natural/memory/"+plain["id"])
    assert not manager.retrieve(principal,"kalender")


def test_vocabulary_expansion_is_bounded_and_does_not_invent_unknown_associations():
    assert "fietsen" in expand({"wielrennen"})
    assert expand({"lantaarn"})==["lantaarn"]
    assert len(expand({str(number) for number in range(100)}))<=24
