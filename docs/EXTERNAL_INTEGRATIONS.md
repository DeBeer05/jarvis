# Externe adapters en beeldcontext

Alle adapters hergebruiken de server, bestaande gesloten toolregistry,
apparaatrechten, scheduler en ApprovalManager. Er is geen automatische ontdekking
van uitvoerbare plugins of door een model gegenereerde code. De componenten zijn
voorbereid; echte configuratie/toestemming blijft apart van technische tests.

## Home Assistant

- Officiële REST API via HTTPS met normale certificaatvalidatie. Configureer als
  eigenaar de basis-URL, toegestane entiteiten en eigen namen. Ondersteund: light,
  switch, climate, sensor, binary_sensor, scene en bestaande automation-routines.
- Sleutel uitsluitend lokaal, verborgen invoer:
  `.venv/Scripts/python.exe scripts/configure_external_secret.py home-assistant`.
  Het script doet geen netwerkverzoek en migreert geen database. Het gebruikt de
  bestaande DPAPI-/beschermde-key-vault; nooit plaintext fallback. Voer geen
  sleutel in chat, clientinstellingen, Git of een opdrachtregelargument in.
- Tokens zijn aan het ingestelde endpoint gebonden. Een endpoint-/allowlist- of
  credentialwijziging maakt bestaande voorstellen ongeldig. Alleen actuele
  rechten en een exacte eenmalige approval kunnen een mutatie uitvoeren.
- Lamp-/thermostaatstatus wordt na de serviceaanroep teruggelezen. Ontbrekende
  bevestiging blijft onzeker en wordt niet blind herhaald. Scene-/routinetriggers
  melden uitsluitend een geaccepteerd startverzoek, geen bewezen afronding.
- Gesprekken gebruiken eigenaaraliassen zonder extra classifier. De interface
  toont configuratie/voorstellen; volledige nieuwe formulieren volgen fase 8.

## Routes, ritkosten en onderhoud

- Openrouteservice directions v2, met de bestaande openbare Open-Meteo-geocoder
  voor eenduidige plaatsnamen. Geen adres wordt verzonnen. De API geeft expliciet
  `live_traffic=false`: een berekende duur is geen actuele verkeerswaarneming.
- Verborgen lokale sleutel: dezelfde configurator met `openrouteservice`.
  Zonder sleutel worden bij een routevraag ook geen plaatsnamen verstuurd.
- Routecache 10 minuten, geocache begrensd; geen periodieke LLM-aanroepen. In
  privémodus geen route-upload. Er wordt geen abonnement of tegoed gekocht.
- Ritkosten worden met Decimal berekend uit opgegeven afstand, verbruik en
  literprijs. Het zijn brandstofkosten, geen geclaimde actuele pompprijzen of
  volledige autokosten. Geen gekoppelde kilometerteller/voertuigtelemetrie.
- Onderhoud op datum gebruikt bestaande persoonlijke routines en herinneringen;
  zonder voertuig-/kilometerbron worden geen automatische kilometerintervallen
  of fysieke voertuigmetingen geclaimd.

## Creality Hi / Cloud

De officiële documentatie bevestigt bediening/monitoring via Creality Cloud,
maar bij dit onderzoek is geen gedocumenteerde publieke Hi-status-API
geverifieerd. Deze adapter staat daarom als niet ondersteund zichtbaar, met
een link naar het officiële dashboard. Geen privé-app-API, wachtwoordopslag,
scraping of verzonnen printerstatus. Dit blokkeert andere adapters niet.

## Beeldcontext

- Windows maakt een voorbeeld uitsluitend op de Qt-hoofdthread; Android leest
  uitsluitend een door de gebruiker gekozen afbeelding. Geen permanente capture,
  MediaProjection-service, camera of opslagtoestemming toegevoegd.
- Globale beeldanalyse en apparaattoestemming staan standaard uit. Cloudbeelden
  vereisen een aparte opt-in. Offline/privé kan cloudanalyse niet omzeilen.
- Het voorbeeld is aan de instellingenrevisie gebonden. Een gewijzigde provider
  vereist opnieuw controleren; geen stille provider-/modelvervanging of fallback.
- PNG maximaal 1,8 MB/twee megapixels; pixeluitpaklimiet, CRC en geen tekst-/ICC-
  metadata. Afbeeldingen worden niet opgeslagen. Alleen numerieke verzoekstatus
  blijft 90 dagen voor quota/idempotentie; mislukte providerpogingen tellen mee.
- Bestaande AI-router/teksttransport, getypeerd observatierapport, geen tools of
  actieautoriteit uit beeldinhoud. Een lokaal model moet via Ollama zelf de
  vision-capability melden. Geen modeldownload of vervanging van Qwen2.5:3B.

## Een adapter toevoegen

Voeg een getypeerd Input-model aan `server/automation/models.py` toe en registreer
het in `REGISTRY`. Markeer mutaties expliciet, neem ze op in `SIDE_EFFECT_TOOLS`
en hergebruik de bestaande executor/guard. Een adapter implementeert begrensde
async I/O met een herhaalde autorisatieguard vóór/na I/O; status en fysieke
afhandeling blijven onderscheiden. Voeg capabilities, mocks, negatieve tests en
zichtbare configuratie toe. Geheimen lopen uitsluitend via de bestaande vault.
Nieuwe rechten worden niet automatisch verleend door een geïnstalleerd bestand.

Bronnen: [HA REST](https://developers.home-assistant.io/docs/api/rest/),
[ORS requests](https://github.com/GIScience/openrouteservice/blob/main/docs/api-reference/endpoints/directions/requests-and-return-types.md),
[Open-Meteo geocoding](https://open-meteo.com/en/docs/geocoding-api),
[Creality support/dashboard](https://cp.crealitycloud.com/service-center),
[Ollama vision](https://github.com/ollama/ollama/blob/main/docs/capabilities/vision.mdx).
