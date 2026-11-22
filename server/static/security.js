"use strict";
const el = id => document.getElementById(id);
const securityNotice = text => { el("security-notice").textContent = text; el("security-notice").hidden = !text; };
const date = value => new Date(value * 1000).toLocaleString("nl-NL");
const node = (tag, text, className) => { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; if (className) element.className = className; return element; };
const action = (title, callback) => { const button = node("button", title, "subtle"); button.type = "button"; button.addEventListener("click", async () => { button.disabled = true; try { await callback(); } catch (error) { securityNotice(error.message); } finally { button.disabled = false; } }); return button; };
const write = (path, body, method = "POST") => JarvisAuth.api(path, {method, ...(body === undefined ? {} : {headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})});
let current = null; let auditOffset = 0; let pairSignature = "";
const scopeNames = {"chat:read": "Gesprekken bekijken", "chat:write": "Chatberichten versturen", "chat:delete": "Gesprekken verwijderen", "status:read": "Serverstatus bekijken", "admin:devices": "Apparaten beheren", "admin:sessions": "Sessies beheren", "admin:account": "Account beheren", "audit:read": "Beveiligingslog bekijken"};
const eventNames = {owner_created: "Eigenaar aangemaakt", login_success: "Inloggen geslaagd", login_failed: "Inloggen mislukt", logout: "Uitgelogd", token_refreshed: "Sessie vernieuwd", refresh_reuse_detected: "Hergebruikt token geblokkeerd", pairing_requested: "Koppeling aangevraagd", pairing_approved: "Koppeling goedgekeurd", pairing_denied: "Koppeling geweigerd", device_paired: "Apparaat gekoppeld", device_revoked: "Apparaat ingetrokken", device_deleted: "Apparaat verwijderd", device_renamed: "Apparaat hernoemd", session_revoked: "Sessie ingetrokken", password_changed: "Wachtwoord gewijzigd", access_denied: "Onbevoegde toegang geblokkeerd"};
async function loadPairs(force = false) {
  const result = await JarvisAuth.api("/api/v1/pairing/requests");
  const signature = JSON.stringify(result.items);
  if (!force && (signature === pairSignature || el("pairing-list").contains(document.activeElement))) return;
  pairSignature = signature; el("pairing-list").replaceChildren();
  if (!result.items.length) el("pairing-list").append(node("p", "Geen open koppelverzoeken.", "muted"));
  for (const item of result.items) {
    const card = node("article", undefined, "security-item"); card.append(node("h3", item.name), node("p", `${item.type} · verloopt ${date(item.expires_at)} · ${item.status === "approved" ? "Goedgekeurd, wacht op apparaat" : "Wacht op jouw goedkeuring"}`, "muted"));
    if (item.status === "pending") {
      const label = node("label", "Code op het nieuwe apparaat"); const code = node("input"); code.autocomplete = "off"; code.maxLength = 16; code.placeholder = "ABCDE-23456"; label.append(code); card.append(label);
      const checks = [];
      for (const scope of item.requested_scopes) { const wrapper = node("label", undefined, "check-label"); const box = node("input"); box.type = "checkbox"; box.checked = ["chat:read", "chat:write"].includes(scope); checks.push([box, scope]); wrapper.append(box, document.createTextNode(scopeNames[scope] || scope)); card.append(wrapper); }
      card.append(action("Koppeling goedkeuren", async () => { await write(`/api/v1/pairing/requests/${item.id}/decision`, {approve: true, user_code: code.value.trim(), scopes: checks.filter(([box]) => box.checked).map(([, scope]) => scope)}); code.value = ""; securityNotice("Koppeling goedgekeurd. Het nieuwe apparaat kan nu zijn sessie ophalen."); await loadAll(); }), action("Weigeren", async () => { await write(`/api/v1/pairing/requests/${item.id}/decision`, {approve: false}); await loadPairs(); }));
    } el("pairing-list").append(card);
  }
}
async function loadDevices() {
  const result = await JarvisAuth.api("/api/v1/devices"); el("device-list").replaceChildren();
  for (const item of result.items) {
    const card = node("article", undefined, "security-item"); card.append(node("h3", item.name + (item.id === current.device_id ? " · dit apparaat" : "")), node("p", `${item.type} · ${item.revoked_at ? "Ingetrokken" : "Vertrouwd"} · laatst actief ${date(item.last_seen)}`, "muted"), node("p", item.permissions.map(scope => scopeNames[scope] || scope).join(" · "), "scope-list"));
    if (!item.revoked_at) {
      const label = node("label", "Apparaatnaam"); const name = node("input"); name.value = item.name; name.maxLength = 80; label.append(name); card.append(label);
      card.append(action("Naam opslaan", async () => { await write(`/api/v1/devices/${item.id}`, {name: name.value}, "PATCH"); await loadDevices(); }));
    }
    const confirm = node("label", undefined, "check-label"); const box = node("input"); box.type = "checkbox"; confirm.append(box, document.createTextNode("Ik bevestig het intrekken of verwijderen van dit apparaat")); card.append(confirm);
    if (!item.revoked_at) card.append(action("Apparaat intrekken", async () => { if (!box.checked) { securityNotice("Bevestig eerst dat je dit apparaat wilt intrekken."); return; } await write(`/api/v1/devices/${item.id}/revoke`); if (item.id === current.device_id) location.assign("/login"); else await loadAll(); }));
    card.append(action("Apparaat verwijderen", async () => { if (!box.checked) { securityNotice("Bevestig eerst dat je de registratie en sessies van dit apparaat wilt verwijderen."); return; } await write(`/api/v1/devices/${item.id}`, undefined, "DELETE"); if (item.id === current.device_id) location.assign("/login"); else await loadAll(); }));
    el("device-list").append(card);
  }
}
async function loadSessions() {
  const result = await JarvisAuth.api("/api/v1/auth/sessions"); el("session-list").replaceChildren();
  for (const item of result.items) {
    const card = node("article", undefined, "security-item"); card.append(node("h3", `${item.device_name}${item.current ? " · huidige sessie" : ""}`), node("p", `${item.revoked_at ? "Ingetrokken" : item.expires_at * 1000 <= Date.now() ? "Verlopen" : "Actief"} · aangemaakt ${date(item.created_at)} · geldig tot ${date(item.expires_at)}`, "muted"));
    if (!item.revoked_at && item.expires_at * 1000 > Date.now()) card.append(action("Sessie intrekken", async () => { await write(`/api/v1/auth/sessions/${item.id}`, undefined, "DELETE"); if (item.current) location.assign("/login"); else await loadSessions(); }));
    el("session-list").append(card);
  }
}
async function loadAudit(append = false) {
  if (!append) { auditOffset = 0; el("audit-list").replaceChildren(); }
  const result = await JarvisAuth.api(`/api/v1/security/audit?limit=50&offset=${auditOffset}`);
  for (const item of result.items) el("audit-list").append(node("p", `${date(item.occurred_at)} · ${eventNames[item.event] || item.event}${item.reason ? " · " + item.reason : ""}`, "audit-row"));
  auditOffset += result.items.length; el("audit-more").hidden = !result.has_more;
}
async function loadAll() { await Promise.all([loadPairs(true), loadDevices(), loadSessions(), loadAudit()]); }
el("security-refresh").addEventListener("click", () => loadAll().catch(error => securityNotice(error.message)));
el("security-logout").addEventListener("click", () => JarvisAuth.logout().catch(error => securityNotice(error.message)));
el("audit-more").addEventListener("click", () => loadAudit(true).catch(error => securityNotice(error.message)));
el("password-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    if (el("new-password").value !== el("repeat-password").value) throw new Error("De nieuwe wachtwoorden komen niet overeen.");
    const result = await write("/api/v1/auth/password", {current_password: el("current-password").value, new_password: el("new-password").value, revoke_all_sessions: el("revoke-sessions").checked});
    if (result.all_sessions_revoked) { sessionStorage.setItem("jarvis_auth_notice", "Wachtwoord gewijzigd. Log opnieuw in met je nieuwe wachtwoord."); location.assign("/login"); }
    else securityNotice("Wachtwoord gewijzigd.");
  } catch (error) { securityNotice(error.message); }
  finally { for (const id of ["current-password", "new-password", "repeat-password"]) el(id).value = ""; }
});
JarvisAuth.initialize().then(async principal => { current = principal; await loadAll(); }).catch(error => securityNotice(error.message));

setInterval(() => { if (current?.permissions.includes("admin:devices") && document.visibilityState === "visible") loadPairs().catch(error => securityNotice(error.message)); }, 5000);
