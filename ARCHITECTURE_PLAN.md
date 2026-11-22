# Architectuurplan — uitsluitend ontwerp

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
