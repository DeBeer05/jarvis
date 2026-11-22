# Architectuurplan — fase 1 en toekomstig ontwerp

## Gerealiseerd in fase 1

De lokale serverbasis in `server/` is nu geïmplementeerd met FastAPI/Uvicorn,
één worker, uitsluitend 127.0.0.1, lifespan-beheer, centrale .env-config,
health/ready/status en SQLite-schema versie 1. Er worden geen bestaande GUI,
cloudhost, pluginworkers, AI-providers of routines geïmporteerd/geactiveerd.
De bestaande netwerkservers zijn onderzocht: dashboard bindt op alle
netwerkinterfaces; core/cloud start ook Telegram/taken/routines en deploycode.
Die behouden hun oorspronkelijke functie en blijven buiten deze lokale basis.

Nieuwe grenzen: `server/config.py` voor configuratie, `database.py` voor korte
SQLite-verbindingen/migraties, `logging_config.py` voor roterende JSON-logs,
`app.py`/`api/` voor lifespan en routers, `control.py` voor lokaal procesbeheer.
Status is tot loopback beperkt; shutdown vereist een apart lokaal controletoken.
Geen publieke authenticatie/deployment ontwerpen via deze lokale toegang.

Gemeten op de ontwikkelwerkplek: 46,90 MiB working set, 34,70 MiB private memory,
844,2 ms processtart tot waargenomen gereedmelding en 1141 ms inclusief Windows-
startscript. Korte idleproef van 3,013 s gaf 0,000% op één-kernschaal; dit is een
momentopname, geen garantie voor de uiteindelijke 8-GB-mini-pc. Details en grenzen:
[docs/HEADLESS_SERVER.md](docs/HEADLESS_SERVER.md).
Onderstaande onderdelen blijven plannen voor latere expliciete opdrachten.

## Doel en grenzen

Een persoonlijke, niet-commerciële JARVIS-assistent op een Windows-mini-pc met
8 GB RAM, met een Windows Desktop Client en een toekomstige Android-app.
Mark-LVII is de bestaande basis; fase 0 bouwt of activeert geen onderdelen.
Onderstaande keuzes zijn voorstellen voor latere bespreking en meting.

## Hybride AI en beperkte hardware

Lichte lokale verwerking voor bediening, beleidscontrole, taakstatus en caching.
Zware redenering of multimodale verzoeken via een instelbare cloudprovider met
expliciete dataminimalisatie, kostenlimieten en time-outs. Hergebruik van
`providers/` en `core/` eerst beoordelen. Offline-modellen alleen na RAM-/CPU-
metingen en een nieuwe opdracht; geen aanname dat een groot LLM binnen 8 GB past.
Voorgesteld uitgangspunt: één zware taak tegelijk, begrensde wachtrij/cache,
geen model op voorhand resident en voldoende ruimte voor Windows en de GUI.
Haalbaarheid, latency, energiegebruik en geheugenverbruik zijn nog onbewezen.

## Componentgrenzen

- Windows-client: bestaande Qt-UI in `gui/` als uitgangspunt; bediening, duidelijke
  toestemmingen, microfoonstatus, taakstatus en herstelbare fouten.
- Serverlaag: toekomstige geauthenticeerde interface en taakcoördinatie. Eerst
  het bestaande `dashboard/` beoordelen; geen tweede server zonder onderbouwing.
- Android-app: toekomstige dunne client voor taken, status en notificaties;
  geen providergeheimen opnemen in een APK.
- Integraties: afzonderlijke adapters met minimale rechten; tokens serverzijdig
  in een OS-secretstore bewaren, buiten Git, logs en mobiele builds.

## Externe toegang

Standaard uit en lokaal begrensd. Voorstel voor later: private VPN of beoordeelde
tunnel met TLS, sterke apparaatauthenticatie, intrekbare sessies, rate limits en
auditinformatie zonder inhoudelijke persoonsgegevens. Geen open port forwarding.
Het bestaande dashboard is niet automatisch goedgekeurd voor internetpublicatie.
Geen service, certificaat, firewallregel of deployment aangemaakt in fase 0.

## Geplande koppelingen

| Onderdeel | Ontwerp voor later |
| --- | --- |
| Agenda en Gmail | OAuth met minimale scopes; lezen en schrijven scheiden; verzending bevestigen |
| Berichtenintegraties | Officiële ondersteunde APIs/voorwaarden beoordelen; per ontvanger toestemming en zichtbare status |
| Internetbellen | VoIP/SIP-provider, kosten, identiteit en expliciete belbevestiging eerst uitwerken |
| Zelfstandige automatiseringen | Duurzame taakstatus, beperkte rechten, herhaalveiligheid, retries met limiet, noodstop en stille uren |

Geen Google-account, berichtenaccount of telefoniedienst gekoppeld. De bestaande
upstreammogelijkheden zijn hiermee niet getest, geactiveerd of veilig verklaard.
Bij autonome acties onderscheid maken tussen lezen, omkeerbare acties en acties
zoals verzenden/bellen/verwijderen die afzonderlijke toestemming vereisen.

## Kwaliteit en beslismomenten

Latere tests: unit-/contracttests per adapter, Qt-threadgrenzen, mobiele
authenticatie, autorisatie, foutpaden, taakherstel en 8-GB-belasting. Geen echte
persoonsgegevens in fixtures. Logging maskeert tokens en standaard geen inhoud.
Voor ontwikkeling nog besluiten: protocol, packaging, databewaring, spraakstack,
providerbudget en client-/serverversies. Geen technologie vastzetten via installatie
of applicatiecode in fase 0.
