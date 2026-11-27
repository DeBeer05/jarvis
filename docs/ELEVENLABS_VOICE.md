# Premium Nederlandse stem

ElevenLabs is een TTS-provider van de bestaande TTSRouter, geen ElevenAgents-
gesprekspartner. Gesprek, geheugen, persoonlijkheid en approvals blijven JARVIS.
Alle providers leveren begrensde mono PCM16 WAV via dezelfde beveiligde route.
ElevenLabs wordt als PCM-stream gelezen. Clients spelen de bestaande zinssegmenten
af terwijl AI verder genereert: geen nieuw full-duplex WebSocketprotocol of
afspelen vanaf de allereerste PCM-byte. Barge-in stopt output, HTTP en generatie
via bestaande annulering/epochs. Geen cloning of betaald stemontwerp aangeroepen.

## Sleutel en gekozen stem

`python scripts/configure_elevenlabs.py` vraagt de sleutel onzichtbaar in de eigen
terminal. Windows bewaart hem gebruikersgebonden met DPAPI buiten het project;
POSIX vereist een owner-only sleutelbestand. De backend leest
`ELEVENLABS_API_KEY_FILE`; een omgevingssecret `ELEVENLABS_API_KEY` kan ook.
Geen API-key in clients, settings-export, Git of logs. `ELEVENLABS_VOICE_ID` is
de backendstandaard; een gekozen ID in centrale instellingen gaat voor.
De eigenaar heeft zijn bestaande ontworpen butlerstem beluisterd en bevestigd;
de persoonlijke Voice ID staat alleen in de lokale configuratie.

## Modi en bediening

| Modus | Werkelijke selectie |
|---|---|
| Premium | Gekozen ElevenLabs-model binnen ingestelde grenzen |
| Automatisch | Premium als sleutel én stem bewust geconfigureerd zijn, anders lokaal |
| Budget | Flash v2.5 binnen dezelfde expliciete grenzen |
| Lokaal | Supertonic/Piper, geen externe synthese |
| Offline | Lokale synthese én lokale AI-routering |

Android heeft nog een bereikbare backend nodig. Offline op de server betekent
geen externe AI/TTS, niet dat een telefoon zonder netwerk een cloudserver bereikt.
Windows kan bij ontbrekende serververbinding uitsluitend reeds geïnstalleerde
lokale modellen gebruiken.

‘Spraak en stem’ en Voice Studio gebruiken de bestaande centrale Settings Manager.
Voice ID, model, supported stability/similarity/style/boost, snelheid, volume,
streaming, fallback en grenzen zijn bruikbaar. Flash toont geen style/boost;
v3 alleen stability; v4 geen genegeerde oude regelaars. Accountmetadata verifieert
Nederlandse TTS-modellen en toegankelijke stemmen. Stemmen met custom sharing
rates worden uitgesloten. Legacy premium-snelheid wordt begrensd op 0,7–1,2;
v3-stability op een ondersteunde discrete waarde. Achter elkaar vergelijken
gebruikt uitsluitend lokale stemmen om onbedoelde premiumaanvragen te vermijden.

## Kosten en privacy

Schema 8 bewaart in `voice_usage` alleen eigenaar, tijd, aantallen en status.
SQLite reserveert atomair vóór synthese. Standaard 2000 gereserveerde credits/dag
en 10000/maand; 0 schakelt premium uit. Dit zijn conservatieve schattingen, geen
factuur of gegarandeerd eurobedrag. Kortingen worden niet vooraf uitgegeven.
Accounttegoed wordt vóór iedere TTS-aanvraag gelezen; Voice Studio toont de
laatst gecontroleerde momentopname. Andere applicaties kunnen hetzelfde account
gebruiken. Accountbrede overage moet de eigenaar zelf bij ElevenLabs beheren.
Er zijn geen routes om abonnementen, extra credits of automatische overage te kopen.

Begonnen/geannuleerde/onzekere aanvragen kunnen credits kosten en blijven
gereserveerd. Een cachetreffer maakt geen nieuwe TTS-aanvraag. Een previewbody
kan de opgeslagen kostengrenzen niet verhogen. Fallback kan vóór succesvolle
audio; een fout na afgeleverde audio stopt de stem om geen dubbele/andere stem
over het antwoord heen te starten. Geschreven antwoord en volgende lokale
antwoordmogelijkheid blijven behouden.

Sleutels, herkenbare tokens en expliciete credentialtekst worden vóór spraakopmaak
afgewezen. Gevoelige termen gaan standaard lokaal. Dit vangnet herkent niet alle
persoonsgegevens; premium verstuurt de uitgesproken tekst naar ElevenLabs.
Enterprise zero-retention wordt niet beloofd. Geen extra opnamen opslaan; cache
blijft tijdelijk en gebonden aan sessie en geheugenversie.

## Primaire bronnen (25 november 2026 gecontroleerd)

- [Stream-API](https://elevenlabs.io/docs/api-reference/text-to-speech/stream)
- [Modellen/Nederlands](https://elevenlabs.io/docs/overview/models)
- [Modelmogelijkheden](https://elevenlabs.io/docs/api-reference/models/list)
- [Accounttegoed](https://elevenlabs.io/docs/api-reference/user/subscription/get)
- [Accountstemmen](https://elevenlabs.io/docs/api-reference/voices/search)

Uitgevoerd bewijs staat in ELEVENLABS_TEST_REPORT.md.
