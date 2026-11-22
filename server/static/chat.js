"use strict";
const $ = (id) => document.getElementById(id);
const state = {conversation: null, request: null, running: false, offset: 0, modeLoaded: false};
const notice = (text = "") => { $("notice").textContent = text; $("notice").hidden = !text; };
async function api(path, options = {}) {
  const response = await fetch(path, {cache: "no-store", ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message || data.detail || "Dit verzoek is niet gelukt.");
  return data;
}
function scrollDown() { $("feed").scrollTop = $("feed").scrollHeight; }
function addMessage(role, text = "", model = "") {
  $("welcome").hidden = true;
  const article = document.createElement("article"); article.className = `message ${role}`;
  if (role === "assistant") {
    const label = document.createElement("div"); label.className = "message-label"; label.textContent = "JARVIS";
    const info = document.createElement("small"); info.textContent = model; label.append(info); article.append(label);
  }
  const body = document.createElement("div"); body.className = "message-text"; body.textContent = text; article.append(body);
  const result = document.createElement("div"); result.className = "message-state"; article.append(result);
  $("messages").append(article); scrollDown(); return article;
}
function setRunning(value) {
  state.running = value; $("send").hidden = value; $("stop").hidden = !value;
  $("provider").disabled = value; $("new-chat").disabled = value; $("message").disabled = value;
  document.querySelectorAll(".history-open,.delete,[data-prompt]").forEach(el => el.disabled = value);
}
async function loadHistory(append = false) {
  if (!append) { state.offset = 0; $("conversations").replaceChildren(); }
  const data = await api(`/api/v1/chat/conversations?limit=50&offset=${state.offset}`);
  for (const item of data.items) {
    const row = document.createElement("div"); row.className = "history-row" + (item.id === state.conversation ? " selected" : "");
    const open = document.createElement("button"); open.className = "history-open"; open.textContent = item.title; open.title = item.title;
    open.addEventListener("click", () => openConversation(item.id).catch(e => notice(e.message)));
    const remove = document.createElement("button"); remove.className = "delete"; remove.textContent = "×"; remove.setAttribute("aria-label", `Verwijder gesprek: ${item.title}`);
    remove.addEventListener("click", async () => {
      if (state.running || !confirm("Dit gesprek definitief verwijderen?")) return;
      try { await api(`/api/v1/chat/conversations/${item.id}`, {method: "DELETE"}); if (state.conversation === item.id) newChat(); else await loadHistory(); }
      catch (e) { notice(e.message); }
    }); row.append(open, remove); $("conversations").append(row);
  }
  state.offset += data.items.length; $("more-history").hidden = !data.has_more;
  if (!$("conversations").children.length) { const empty = document.createElement("p"); empty.className = "empty-history"; empty.textContent = "Nog geen gesprekken.\nJe eerste idee is een goed begin."; $("conversations").append(empty); }
  setRunning(state.running);
}
function newChat() {
  if (state.running) return;
  state.conversation = null; $("messages").replaceChildren(); $("welcome").hidden = false; $("chat-title").textContent = "Een nieuw perspectief begint hier.";
  notice(); $("message").value = ""; $("message").focus(); loadHistory().catch(e => notice(e.message));
}
async function openConversation(id) {
  if (state.running) return;
  const data = await api(`/api/v1/chat/conversations/${id}`); state.conversation = id;
  $("messages").replaceChildren(); $("welcome").hidden = true; $("chat-title").textContent = data.title; notice();
  for (const turn of data.turns) {
    addMessage("user", turn.user_text);
    const answer = addMessage("assistant", turn.assistant_text, [turn.provider, turn.model].filter(Boolean).join(" · "));
    if (turn.status !== "completed") answer.querySelector(".message-state").textContent = turn.status === "cancelled" ? "Antwoord gestopt." : turn.error?.message || "Dit antwoord is niet voltooid. Je kunt een nieuw bericht sturen.";
  } await loadHistory(); scrollDown();
}
async function refreshProviders() {
  try {
    await api("/ready"); $("connection").textContent = "Lokaal verbonden"; $("connection-dot").classList.remove("offline");
    const data = await api("/api/v1/ai/providers");
    if (!state.modeLoaded) { $("provider").value = data.mode; state.modeLoaded = true; }
    const gem = data.providers.gemini; const oll = data.providers.ollama; const groq = data.providers.groq;
    $("model-status").textContent = `${gem.model} · ${gem.configured ? "sleutel ingesteld" : "sleutel ontbreekt"}  /  ${groq?.model || "Groq"} · ${groq?.configured ? "sleutel ingesteld" : "sleutel ontbreekt"}  /  ${oll.model} · ${oll.available ? "beschikbaar" : oll.state === "model_missing" ? "model ontbreekt" : "Ollama offline"}`;
  } catch (e) { $("connection").textContent = "Server niet bereikbaar"; $("connection-dot").classList.add("offline"); $("model-status").textContent = "Controleer de lokale server op poort 8765."; }
}
async function sendMessage(event) {
  event.preventDefault(); const message = $("message").value.trim(); if (!message || state.running) return;
  const requestId = crypto.randomUUID(); state.request = requestId;
  addMessage("user", message); const answer = addMessage("assistant"); answer.classList.add("streaming");
  $("message").value = ""; $("message").style.height = "32px"; setRunning(true); notice(); let finalReceived = false;
  try {
    const response = await fetch("/api/v1/chat/stream", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({message, provider: $("provider").value, conversation_id: state.conversation, request_id: requestId})});
    if (!response.ok) { const data = await response.json(); throw new Error(data.error?.message || data.detail || "Het bericht kon niet worden verstuurd."); }
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
    while (true) {
      const {value, done} = await reader.read(); if (done) break;
      buffer += decoder.decode(value, {stream: true}); let split;
      while ((split = buffer.indexOf("\n\n")) >= 0) {
        const frame = buffer.slice(0, split); buffer = buffer.slice(split + 2);
        const dataLine = frame.split("\n").find(line => line.startsWith("data: ")); if (!dataLine) continue;
        const data = JSON.parse(dataLine.slice(6));
        if (data.type === "meta") { state.conversation = data.conversation_id; $("chat-title").textContent = message.slice(0, 72); }
        else if (data.type === "provider") answer.querySelector("small").textContent = `${data.provider} · ${data.model}`;
        else if (data.type === "delta") { answer.querySelector(".message-text").textContent += data.text; scrollDown(); }
        else if (data.type === "fallback") notice(`Overschakelen van ${data.from} naar ${data.to}. ${data.message}`);
        else if (data.type === "error") { notice(data.message); answer.querySelector(".message-state").textContent = data.message; }
        else if (data.type === "done") {
          finalReceived = true; answer.querySelector(".message-text").textContent = data.message;
          if (data.status === "cancelled") answer.querySelector(".message-state").textContent = "Antwoord gestopt. Het ontvangen deel is bewaard.";
          if (data.status === "completed") notice();
        }
      }
    }
    if (!finalReceived) throw new Error("De verbinding werd onderbroken voordat het antwoord klaar was.");
  } catch (e) { notice(e.message); answer.querySelector(".message-state").textContent = e.message; }
  finally { answer.classList.remove("streaming"); state.request = null; setRunning(false); $("message").focus(); await loadHistory().catch(e => notice(e.message)); }
}
$("composer").addEventListener("submit", sendMessage);
$("stop").addEventListener("click", async () => { if (!state.request) return; try { await api(`/api/v1/chat/requests/${state.request}/cancel`, {method: "POST"}); } catch (e) { notice(e.message); } });
$("new-chat").addEventListener("click", newChat);
$("refresh-providers").addEventListener("click", refreshProviders);
$("more-history").addEventListener("click", () => loadHistory(true).catch(e => notice(e.message)));
$("message").addEventListener("input", () => { $("message").style.height = "32px"; $("message").style.height = `${Math.min($("message").scrollHeight,160)}px`; });
$("message").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("composer").requestSubmit(); } });
document.querySelectorAll("[data-prompt]").forEach(button => button.addEventListener("click", () => { $("message").value = button.dataset.prompt; $("message").focus(); }));
Promise.all([loadHistory(), refreshProviders()]).catch(e => notice(e.message));
setInterval(refreshProviders, 30000);
