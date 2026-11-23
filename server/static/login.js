"use strict";
const loginNotice = document.getElementById("login-notice");
const showLoginNotice = text => { loginNotice.textContent = text; loginNotice.hidden = !text; };
showLoginNotice(sessionStorage.getItem("jarvis_auth_notice") || "");
sessionStorage.removeItem("jarvis_auth_notice");
function loginDestination() {
  const destination=sessionStorage.getItem("jarvis_after_login");
  sessionStorage.removeItem("jarvis_after_login");
  return ["/automations#oauth","/automations?google=all#oauth"].includes(destination)?destination:"/chat";
}
async function prepareLogin() {
  let current = await fetch("/api/v1/auth/session", {cache: "no-store"});
  if (!current.ok && JarvisAuth.csrf()) {
    try { await JarvisAuth.restore(); current = await fetch("/api/v1/auth/session", {cache: "no-store"}); } catch { /* Fresh login remains available. */ }
  }
  if (current.ok) { location.replace(loginDestination()); return; }
  const response = await fetch("/api/v1/auth/status", {cache: "no-store"});
  if (!response.ok) throw new Error("De server is niet beschikbaar. Probeer later opnieuw.");
  const state = await response.json();
  document.getElementById("setup-help").hidden = !state.setup_required;
  document.getElementById("login-form").hidden = state.setup_required;
  await fetch("/api/v1/auth/csrf", {cache: "no-store"});
}
document.getElementById("login-form").addEventListener("submit", async event => {
  event.preventDefault(); const button = document.getElementById("login-button"); button.disabled = true;
  try {
    await JarvisAuth.api("/api/v1/auth/login", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({username: document.getElementById("username").value, password: document.getElementById("password").value, device_name: "Browser"})});
    location.replace(loginDestination());
  } catch (error) { showLoginNotice(error.message); await fetch("/api/v1/auth/csrf", {cache: "no-store"}); }
  finally { button.disabled = false; document.getElementById("password").value = ""; }
});
prepareLogin().catch(error => showLoginNotice(error.message));
