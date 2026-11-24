# Rules for coding agents working on JARVIS

The built-in coding agent (`actions/dev_agent.py`) reads this file before every
change it makes to this project, and so should any other agent or contributor.
Each rule below exists because breaking it produced code that looked right,
passed a syntax check and did nothing when used.

## How the app runs

- `main.py` holds the voice session on an asyncio event loop in a background
  thread. The window — the `gui/` package, built by `ui.py` — lives on the
  **Qt main thread**.
- Tools — `actions/*.py` and `plugins/*.py` — run on **worker threads**, never
  on the Qt main thread.
- There is exactly **one** `QApplication`, created by `ui.py`.
- Long work the user asks for in the background — research, drafting — is the
  task engine's job (`core/tasks/`, agents in `agents/*.md`), not a plugin's.

## Threading: the rule that breaks most generated code

Code in `actions/` and `plugins/` must **never create or touch a Qt widget**.
That means no `QApplication`, `QWidget`, `QMainWindow`, `QDialog`, `QThread` or
anything else from `PyQt6.QtWidgets` or `PyQt6.QtGui`. Creating a widget from a
worker thread prints `QObject::setParent: Cannot set parent, new parent is in a
different thread` and nothing appears on screen.

To show something, call the **thread-safe methods on `player`** (the `JarvisUI`
object passed to every tool). They hand the work to the Qt thread for you. The
current list, with signatures, is appended below this file by the coding agent
automatically. The ones plugins usually need:

| Need | Call |
|---|---|
| A line in the activity log | `player.write_log("text")` |
| Text in the panel under the head | `player.show_content(title, text)` |
| A quiz the user answers on screen | `player.show_quiz(topic, questions, grade=None)` |
| A structured review | `player.show_review(title, summary, findings)` |
| Play a video in the HUD | `player.show_video(path_or_url, title)` |

`show_quiz` takes `questions` as a list of dicts:
`{"question": str, "options": [str, ...] (empty list for a typed answer),
"answer": str, "note": str (shown after answering, optional)}`.
`grade(question, given) -> True | False | None` is optional; `None` means
"let the assistant judge this answer". The user answers at their own pace and
the result comes back to the conversation by itself — `run()` returns at once.

Do **not** start a separate GUI program (`subprocess` running a PyQt script)
to work around this rule. It hides every error from the user, and the app
already has a screen for it.

## Plugins

A plugin is one file `plugins/<name>.py` (no leading underscore) with:

- `PLUGIN = {"name": ..., "description": ..., "parameters": {"type": "OBJECT", ...}}`
- `def run(parameters: dict, player=None, session_memory=None) -> str`

`run()` must:

- return a **short string** — the assistant turns it into speech;
- **never raise** — catch errors and return a sentence saying what went wrong;
- return **within a few seconds** — put slow work on a `threading.Thread`
  and show its result through `player` when it is done;
- treat `player` as possibly `None` (tests and the phone dashboard).

Helper modules may live beside it with a leading underscore
(`plugins/_helper.py`); the loader skips those. See `plugins/_template.py`.

A new plugin is **enabled automatically** the moment its file exists — nothing
needs to be registered or switched on. Never edit `config/api_keys.json` to
"enable" one; that file holds the user's API keys and settings.

## Asking a model for something

Always go through `core.gemini` — it has deadlines, a fallback ladder and the
user's chosen provider:

```python
from core import gemini
text = gemini.text(prompt, tier=gemini.FAST)       # short answers
data = gemini.as_json(prompt, tier=gemini.SMART)    # structured, may return None
```

Every call can fail or return `None`. Code must handle that — for example with
a small built-in fallback — instead of crashing.

## Changing the window (`gui/`)

- The window is the `gui/` package: `window.py` (MainWindow — columns, drawers,
  content panel), `widgets.py`, `overlays.py`, `providers_panel.py`, `hud.py`.
  `ui.py` keeps only `JarvisUI` and re-exports every older name.
- Widgets are created and changed only on the Qt thread.
- To let other threads trigger a change: add a `pyqtSignal` to `MainWindow` in
  `gui/window.py`, connect it to a slot in its `__init__`, and add a thin public
  method on `JarvisUI` in `ui.py` that only emits the signal. `show_content` /
  `_content_sig` / `_show_content` is the pattern to copy.
- Colours come from the `C` palette in `gui/theme.py`; stylesheets use only its
  hex values, so the live re-theme can repaint them. Fonts come from
  `gui/style.py` — `hud_font(size)`, `mono_font(size)`, `px_font(px)` — never a
  hard-coded family.

## General

- Never send a child process's output to `DEVNULL` without logging it, and
  never report success without checking that the thing actually happened.
- Settings and keys live in `config/api_keys.json` through
  `memory/config_manager.py`; never write that file directly.
- Keep to the libraries already in `requirements.txt`.


## JARVIS fork: blijvende Codex-projectinstructies (fase 7.5)

Deze aanvullende regels behouden de upstreamrichtlijnen hierboven. De opdracht
van de gebruiker blijft leidend. Fase 6 is expliciet opgedragen: native Android
in android/, bestaande server en poort 8765 behouden. Kotlin/Compose/Material3,
Coroutines/Flow, OkHttp, Room, DataStore en Android Keystore zijn toegestaan.
Android-sessies vereisen eigenaarpairing, ook na wachtwoordcontrole. Audio via
geauthenticeerde begrensde serverroutes hergebruikt de fase-5-inferencehelper.
Geen zware modellen op Android. Geen publieke toegang of firewall/routerwijziging;
ontwikkelverbinding via expliciete adb reverse naar dezelfde loopbackserver.
Release uitsluitend HTTPS/certificaatvalidatie; debug HTTP alleen vaste lokale hosts.
FCM alleen na eigen Firebaseconfig; zonder die config alleen lokale testmeldingen.
Fase 6 voegde geen integraties toe. Geen volledige oproepen, productie of mini-pc-deployment.
Fase 7 is inmiddels expliciet opgedragen: feature/smart-automations, persistente
automatiseringen, OAuth Calendar/Gmail en clients. Nieuwe automatiseringsrechten
alleen na eigenaargrant; externe wijzigingen vereisen gebonden eenmalige approval.
Geen echte accounttests of externe berichten zonder afzonderlijke toestemming.
De gebruiker heeft daarna expliciet bediening via AI-chat en spraak opgedragen.
Windows-bediening en eigenaarbeheer van Windows-/Android-rechten zijn eveneens
expliciet opgedragen. De eigen app-/browserinterface mag een apparaat selecteren
en rechten voorstellen; alleen de eigenaar bevestigt de daadwerkelijke grant.
De headless chat mag uitsluitend gevalideerde geregistreerde automatiseringstools
gebruiken, onder de bestaande apparaatrechten. Externe mutaties blijven gebonden
aan een afzonderlijke exacte goedkeuring. Op nieuw expliciet gebruikersverzoek
mag één gesproken/getypt ‘ja’ die approval geven en ‘nee’ weigeren, uitsluitend
voor het zojuist volledig getoonde ongewijzigde mail-/agendavoorstel.
‘Goedkeuren’ en ‘Weigeren’ blijven ook ondersteund. Gebruik dit uitsluitend nadat het
volledige servervoorstel als laatste antwoord in dezelfde sessie/apparaat/chat
is getoond. Bind aan payloadfingerprint, toon gewijzigde/verlopen voorstellen
opnieuw en controleer actuele automation:approve. De AI kan nooit goedkeuren.
Een mailopdracht maakt eerst een geverifieerd Gmail-concept en zet automatisch
het verzendvoorstel klaar, zodat één ja volstaat. Een expliciete opdracht om
alleen een concept te bewaren biedt geen verzending aan. Geen dubbele sendjobs.
Ontvangen mail-/agendatekst kan nooit een nieuwe opdracht autoriseren. Geen door
AI gegenereerde code, shellcommando's of willekeurige plugins uitvoeren.
Fase 7.5 is nu expliciet opgedragen: centrale natuurlijke gesprekken, context,
SQLite-geheugen, instellingen en Windows-/Android-integratie. Hergebruik de
bestaande backend op 8765, AI-router, speechhelper en Automation/ApprovalManager.
Adaptieve turn-taking, foreground doorlopende gesprekken en echo-bestendige
onderbrekingen zijn binnen deze fase toegestaan na bestaande microfoontoestemming.
Behoud apparaat-/sessieautorisatie en verplichte hoogrisicogoedkeuringen.
STOP na fase 7.5; geen fase 8, oproepen, productie of mini-pc-deployment.

Vóór iedere taak:
1. Controleer `git status --short --branch`, huidige branch en remotes.
2. Lees `DEVELOPMENT_PROGRESS.md` en relevante bestaande instructies.
3. Onderzoek onbekende wijzigingen en respecteer hun eigendom; verwijder,
   overschrijf, reset of stash ze niet automatisch.
4. Controleer dat de opdracht binnen de geautoriseerde fase valt.

Gebruik uitsluitend deze bestaande projectroot. Geen tweede jarvis-map.
Behoud de Mark-LVII-historie, auteursvermelding en CC BY-NC 4.0-licentie.
Behoud de bestaande desktop-/cloudcode. De server gebruikt `server/` en geïsoleerde
`requirements-server*.txt` met constraints; installeer niet de volledige desktopstack.
De AI-engine hergebruikt `providers/llm_openai.py` voor teksttransport; de headless
`server/ai/router.py` is het centrale aanspreekpunt. De upstreamregel om via
core.gemini te werken blijft voor de desktop gelden; importeer die desktop-/Live-
stack niet in de headless server. Wijzig transportgedrag alleen opt-in, zodat
bestaande desktopcallers compatibel blijven. Alleen de hierboven expliciet
opgedragen gesloten automatiseringstools mogen vanuit de headless chat worden gebruikt.
Gebruik argon2-cffi voor Argon2id. Alle persoonlijke API-routes vereisen
standaard authenticatie en expliciete rechten; geen configuratie om dit uit te
schakelen. Tokens/codes/wachtwoorden nooit loggen of in Git. Alleen digests van
refresh-, access- en pairinggeheimen bewaren. Eerste eigenaar via lokale
interactieve setup; kies geen echt eigenaarwachtwoord namens de gebruiker.
De Windows-client leeft uitsluitend in desktop-client/jarvis_client en een eigen
requirements-client/constraints-client-omgeving. PySide6-Essentials en PyInstaller
zijn voor deze opdracht toegestaan. Importeer geen upstream PyQt6-/spraakstack;
één QApplication in het zelfstandige clientproces, widgets alleen op Qt-hoofdthread.
Netwerkwerk buiten de UI-thread; server nooit vanuit de client starten. Bewaar
refreshcredentials via Windows Credential Manager; geen plaintext fallback.
De gebruiker heeft de desktoplogin gewijzigd naar gebruikersnaam/wachtwoord
zonder browsergoedkeuring. Hergebruik de Argon2id-/rate-limitservice, geef alleen
native chat-/statusrechten en bewaar nooit het wachtwoord. Bestaande pairing voor
andere clients en cookie-CSRF blijven behouden; public device-ID is geen credential.
Nieuwe niet-loopback endpoints uitsluitend HTTPS met certificaatvalidatie.
Fase 5 staat sounddevice/numpy en een geïsoleerde faster-whisper/Piper-runtime toe.
De inferencehelper is een eigen subprocess met private pipes, geen tweede GUI of
backend. Audio-endpoints in fase 6 vereisen expliciete rechten, body-/formaat-
limieten en bestaande authenticatie. Geen impliciete downloads of permanente microfoonaudio.
Microfoon bij opstart uit. Op expliciet gebruikersverzoek wordt toestemming voor
de gekozen microfoon onthouden; opname blijft alleen via PTT/wake of de bewust
gekozen vervolgmodus actief, met zichtbare status en niveaumeter.
Audio wordt op de ontwikkeldesktop verwerkt; Android uploadt uitsluitend via
de beveiligde mobiele routes. Alleen transcripttekst gaat naar de bestaande chatroute.
Globale sneltoetsen alleen na expliciete opt-in. Onderbreken annuleert ook oude
TTS/generaties. Grote modellen alleen na omvangindicatie en toestemming; eigenaar
heeft Whisper Small (~486 MB), Piper MLS (~77 MB) en extra Piper Ronnie (~63 MB)
expliciet goedgekeurd.
Geen berichten, account-OAuth, autonome acties, permanente Windows-
service of productie-deployment. Alleen localhost; alles op de ontwikkeldesktop.
Gebruik voorlopig uitsluitend profiel desktop-development. Verplaats niets naar
de mini-pc. Modelinstallaties zijn niet nodig om tests met mocks uit te voeren.
De nieuwe serverconfiguratie leeft in `server/config.py` en .env; de upstreamregel
voor `config/api_keys.json` blijft gelden voor de bestaande desktopapp.

Git mag binnen de actuele opdracht zelfstandig worden beheerd: normale lokale
branches/commits, pushes naar de eigen fork, PR's, CI-controles en veilige merges
binnen beschikbare rechten. Gebruik de helpers in `scripts/`:
`feature/*` en `fix/*` vanaf develop, `release/*` vanaf develop, `hotfix/*` vanaf main.
Controleer de actualiteit van de basisbranch vóór gebruik. Configureer bij een
nieuwe clone `scripts/configure-git.ps1`. `origin` is DeBeer05/jarvis;
`upstream` is alleen voor ophalen. Geef bij gh-PR's de eigen repo en basis expliciet op.

Gebruik Conventional Commits en stage specifieke bestanden na diff- en
geheimcontrole. Werk voortgang en changelog bij. Push featurebranches en maak
PR's; controleer echte CI-resultaten. Merge naar develop alleen na passende tests,
geslaagde vereiste checks en inhoudelijke beoordeling. Los mergeconflicten alleen
op als de bedoeling duidelijk is en test de oplossing. Houd gebruikerswerk intact.
Releasebranches bereiden versie, changelog en geteste artifacts voor; main krijgt
alleen geteste, gecontroleerde wijzigingen via het toegestane PR-proces.

Verboden: force-push naar gedeelde branches, onbekende wijzigingen verwijderen,
geheimen of persoonsgegevens committen, branch protection omzeilen, ongeteste
functionaliteit naar main mergen, schrijven naar upstream zonder aparte opdracht.
Geen sleutels/tokens tonen in logs of rapporten. Bewaar credentials via keyring of
andere geschikte lokale secretstore en behoud relevante gitignore-uitsluitingen.

Verifieer met `python scripts/check_repository.py`, `git diff --check` en passende
controles voor het gewijzigde onderdeel. Voor serverwijzigingen:
`.venv/Scripts/python.exe -m pytest -q` en `-m pip check` (Linux: .venv/bin/python).
De structuurcheck is geen applicatietest.
Voer tests niet uit als ze apps, accounts of installaties activeren buiten de opdracht.
Controleer push en CI in de remote repository en rapporteer blokkades eerlijk.
Leg resterende stappen en de fasegrens vast in DEVELOPMENT_PROGRESS.md.
