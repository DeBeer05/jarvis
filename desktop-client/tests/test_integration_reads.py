import base64

import httpx
import pytest

from jarvis_client.integration_reads import IntegrationReads
from jarvis_client.api import ApiClient
from test_window import window


class Bridge:
    def __init__(self): self.calls=[]
    def call(self,method,path,body,success,failure=None):
        self.calls.append((method,path,body,success,failure))


def test_calendar_names_dates_plaintext_and_late_result(qt):
    bridge=Bridge();view=IntegrationReads(bridge,"calendar");view.set_authorized(True)
    view.calendar_names();bridge.calls[-1][3]({"items":[{"id":"work","summary":"Werk <script>"}]})
    assert view.calendars.itemText(0)=="Werk <script>"
    view.period(1,1);request=bridge.calls[-1]
    assert request[2]["calendar_id"]=="work"
    request[3]({"items":[{"summary":"<img src=x>","start":{"date":"2026-11-24"},"end":{"date":"2026-11-25"},"location":"Testlocatie"}]})
    view.results.setCurrentRow(0)
    assert "<img src=x>" in view.reader.toPlainText() and "hele dag" in view.reader.toPlainText()
    assert "Testlocatie" in view.reader.toPlainText()
    view.calendar();old=bridge.calls[-1][3];view.start.setDate(view.start.date().addDays(1));old({"items":[{"summary":"Old"}]})
    assert view.results.count()==0
    view.clear();assert view.calendars.count()==1 and not view.reader.toPlainText()


def test_mail_metadata_then_explicit_body_and_stale_selection(qt):
    bridge=Bridge();view=IntegrationReads(bridge,"mail");view.set_authorized(True)
    view.mail_search();bridge.calls[-1][3]({"messages":[{"id":"one"},{"id":"two"}]})
    for identifier in ("one","two"):
        assert bridge.calls[-1][1].endswith("/email/"+identifier)
        bridge.calls[-1][3]({"id":identifier,"payload":{"headers":[{"name":"Subject","value":"<script>"},{"name":"From","value":"example@example.invalid"}]}})
    assert view.results.count()==2 and len(bridge.calls)==3
    view.results.setCurrentRow(0);view.mail_body();old=bridge.calls[-1][3]
    assert bridge.calls[-1][1].endswith("/email/one?include_body=true")
    body={"payload":{"mimeType":"text/plain","body":{"data":base64.urlsafe_b64encode("Hallo café <img>".encode()).decode()}}}
    old(body);assert "Hallo café <img>" in view.reader.toPlainText()
    view.results.setCurrentRow(1);old(body);assert "Hallo café" not in view.reader.toPlainText()
    view.mail_body();bridge.calls[-1][3]({"snippet":"Korte weergave","payload":{"mimeType":"text/html","body":{"data":"invalid-html"}}})
    assert "Korte weergave" in view.reader.toPlainText()
    view.set_authorized(False);assert view.results.count()==0 and not view.reader.toPlainText()


def test_loading_failure_and_logout_invalidate_pending_data(qt):
    bridge=Bridge();view=IntegrationReads(bridge,"mail");view.set_authorized(True)
    view.mail_search();request=bridge.calls[-1];request[4](ValueError("Google niet bereikbaar"))
    assert "Google niet bereikbaar" in view.status.text()
    view.clear();request[3]({"messages":[{"id":"old"}]})
    assert len(bridge.calls)==1 and not view.reader.toPlainText()


def test_body_path_is_explicit_and_does_not_enable_arbitrary_query_parameters(vault):
    calls=[]
    def handler(request):calls.append(request);return httpx.Response(200,json={})
    api=ApiClient("http://127.0.0.1:8765",vault,transport=httpx.MockTransport(handler));api.access="synthetic";api.deadline=api.clock()+600
    api.request("GET","/api/v1/automation/email/synthetic-id?include_body=true")
    for path in ("/api/v1/automation/email/id?include_body=true&x=1","/api/v1/automation/email/../../x?include_body=true","/api/v1/automation?x=1"):
        with pytest.raises(ValueError):api.request("GET",path)
    assert len(calls)==1;api.close()


def test_native_permission_banner_and_ai_shortcut_preserve_draft(qt,tmp_path,vault):
    app=window(tmp_path,vault);panel=app.automation_panel
    panel.set_authorized({"chat:write"},True)
    assert not panel.calendar_view.isEnabled() and "automation:read" in panel.access.text()
    panel.set_authorized({"chat:write","automation:read"},True)
    assert panel.calendar_view.isEnabled() and panel.mail_view.isEnabled()
    app.composer.setPlainText("Mijn bestaande bericht");panel.open_chat()
    assert app.composer.toPlainText()=="Mijn bestaande bericht" and app.pages.currentIndex()==0
    panel.clear();app.closing=True;app.tray.hide();app.close()
