"use strict";
window.JarvisAuth = (() => {
  let refreshing = null;
  let timer = null;
  const csrf = () => document.cookie.split("; ").find(row => row.startsWith("jarvis_csrf="))?.slice("jarvis_csrf=".length) || "";
  function schedule(principal) {
    clearTimeout(timer);
    timer = setTimeout(() => refresh().catch(expired), Math.max(1000, principal.access_expires_at * 1000 - Date.now() - 30000));
  }
  function expired() {
    clearTimeout(timer);
    sessionStorage.setItem("jarvis_auth_notice", "Je bent niet ingelogd of je sessie is verlopen. Log in om verder te gaan.");
    location.assign("/login");
  }
  async function refresh() {
    if (refreshing) return refreshing;
    const rotate = async () => {
      // Another tab may already have rotated the shared cookies while this tab waited.
      const current = await fetch("/api/v1/auth/session", {cache: "no-store", credentials: "same-origin"});
      if (current.ok) {
        const principal = await current.json();
        if (principal.access_expires_at * 1000 > Date.now() + 35000) { schedule(principal); return; }
      }
      const response = await fetch("/api/v1/auth/refresh", {method: "POST", credentials: "same-origin", cache: "no-store", headers: {"X-Jarvis-CSRF": csrf()}});
      if (!response.ok) throw new Error("Je sessie kon niet worden vernieuwd.");
      schedule(await response.json());
    };
    refreshing = (navigator.locks ? navigator.locks.request("jarvis-session-refresh", rotate) : rotate()).finally(() => { refreshing = null; });
    return refreshing;
  }
  async function authenticatedFetch(path, options = {}) {
    const target = new URL(path, location.origin);
    if (target.origin !== location.origin) throw new Error("Gebruik de lokale JARVIS-server.");
    const send = () => {
      const headers = new Headers(options.headers || {});
      if (!["GET", "HEAD"].includes((options.method || "GET").toUpperCase())) headers.set("X-Jarvis-CSRF", csrf());
      return fetch(path, {...options, headers, credentials: "same-origin", cache: "no-store"});
    };
    let response = await send();
    if (response.status === 401 && !["/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/token"].includes(target.pathname)) {
      const failure = await response.clone().json().catch(() => ({}));
      if (failure.error?.code === "authentication_required") {
        try { await refresh(); response = await send(); }
        catch { expired(); throw new Error("Log opnieuw in."); }
      }
    }
    return response;
  }
  async function api(path, options = {}) {
    const response = await authenticatedFetch(path, options);
    const result = await response.json();
    if (!response.ok) { const error = new Error(result.error?.message || result.detail || "Het verzoek is niet gelukt."); error.status = response.status; throw error; }
    return result;
  }
  async function initialize() {
    const principal = await api("/api/v1/auth/session"); schedule(principal); return principal;
  }
  async function logout() {
    await api("/api/v1/auth/logout", {method: "POST"}); clearTimeout(timer); location.assign("/login");
  }
  addEventListener("pagehide", () => {
    document.getElementById("messages")?.replaceChildren();
    document.getElementById("conversations")?.replaceChildren();
    for (const id of ["device-list", "session-list", "pairing-list", "audit-list"]) document.getElementById(id)?.replaceChildren();
    document.querySelectorAll('input[type="password"]').forEach(input => { input.value = ""; });
  });
  addEventListener("pageshow", event => { if (event.persisted) location.reload(); });
  return {fetch: authenticatedFetch, api, initialize, logout, expired, csrf, restore: refresh};
})();
