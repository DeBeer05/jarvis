# Privacy van spraak

Microfoon staat bij iedere start uit. De appsessie vraagt een expliciet vinkje;
dat wordt nooit opgeslagen. PTT of een bewust ingeschakelde wakefunctie opent
de opname, zichtbaar in Spraak én op de chatmicrofoonknop. Stop, toestemming
intrekken, sessieverlies en volledig afsluiten stoppen opname en uitvoer.
Het venster naar het systeemvak sluiten beëindigt standby niet; gebruik Stop of
Volledig afsluiten. Geen Windows-microfoonrechten worden automatisch gewijzigd.

Ruwe PCM/WAV, transcriptbewerking en Piper-inferentie blijven lokaal in geheugen
en private helperpipes. Geen audiofiles of transcriptlogs, geen cloud-STT/TTS,
geen audiotelemetrie, geen audio-endpoint. Begrensde input (maximaal 120 s),
tekstqueue (32 segmenten) en optionele RAM-cache (8 MB). Uitloggen leegt ook de
cache en spraakvelden. Geen schijf-audiocache. Windows zelf kan geheugen pagineren;
de app claimt geen bescherming tegen lokale beheerders of OS-geheugendumps.

Herkende opdrachttekst gaat via de bestaande ingelogde client naar de server en
wordt als gewone chat in de bestaande SQLite-geschiedenis opgeslagen. Bij Groq
of Gemini gaat tekst/context naar die externe provider; bij expliciet Ollama
blijft ook de AI-inferentie lokaal mits de lokale server/Ollama beschikbaar zijn.
Standby zonder herkende activatie verstuurt geen tekst naar de server.
AI-antwoorden gaan lokaal naar Piper. Geen AI-gegenereerde acties worden uitgevoerd.

Instellingen bevatten uitsluitend modelpad, apparaten, volumes, gevoeligheid,
sneltoetsen en andere voorkeuren. Geen wachtwoorden/tokens of toestemming.
Refreshcredential blijft in Windows Credential Manager; de helper krijgt nooit
credentials of toegang tot persoonlijke API-routes. Nieuwe remoteprofielen
blijven HTTPS met certificaatvalidatie vereisen.

Logregels bevatten uitsluitend vaste status/foutcategorieën. Native helperoutput
wordt gedraineerd en alleen als categorie gemeld, nooit met audio, modeltekst of
persoonlijke paden doorgeschreven. Modeldownloads zijn aparte bewuste opdrachten;
Hugging Face ontvangt daarbij gewone downloadverzoeken/IP, geen gesprekken.

Knop/sneltoets onderbreken audio en de inferenceprocesboom; generatiecontrole
voorkomt dat oude resultaten later afspelen. Er is geen echo-onderdrukking of
betrouwbare gesproken barge-in: tijdens antwoordweergave is opname uit. Gebruik
een headset en Stop/PTT bij snelle beurtwisseling. De wakefunctie blijft
experimenteel, standaard uit en kan echte kamer-/tvspraak fout herkennen.
