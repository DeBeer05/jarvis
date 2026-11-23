# Android-beveiliging en privacy

Default-deny op de server blijft intact. Een geslaagd Android-wachtwoordverzoek
levert uitsluitend een pairingverzoek op, geen token of beheersessie. S256-bewijs,
eigenaarcodevergelijking en expliciete rechten zijn verplicht. Android krijgt geen
adminrechten; andere apparaten beheer je via de eigenaarinterface.

Refresh is AES-GCM-ciphertext met Android Keystore-sleutel en originbinding.
Access blijft in RAM; wachtwoorden en pairingverifiers worden niet opgeslagen.
Rotatie is geserialiseerd. De oude duurzame refresh wordt vóór rotatie verwijderd;
alleen aantoonbaar falen vóór verzending mag hem herstellen. Onzekere rotatie
vereist opnieuw koppelen en wordt nooit gereplayed. Late login/refreshresultaten
worden na uitloggen geweigerd. Geen tokens in URL's, logs of notificaties.

Room bevat uitsluitend versleutelde gesprekken en metadata, met afzonderlijke
AAD per origin/gesprek. Bij uitloggen/401 wordt cache gewist. Offline intrekking
kan niet direct worden waargenomen; een eerder ontgrendelde telefoon kan eerder
versleuteld bewaarde inhoud tonen tot de volgende online controle. Geen plaintext
fallback. Back-up en apparaattransfer van privébestanden zijn uitgesloten.

TLS en certificaat/hostnamecontrole staan altijd aan. Geen custom trust-all,
geen certificaatuitzondering of redirect-forwarding van credentials. Debug-HTTP
is beperkt via Network Security Configuration én endpointvalidatie tot drie
expliciete lokale hosts. Release heeft geen HTTP-toelating. Een lokaal ADB-
reversekanaal maakt de bestaande loopbackserver bereikbaar zonder LAN-binding.
De service-identiteit wordt via health gecontroleerd; de cryptografische
transportidentiteit van externe servers komt van normale TLS-validatie.

Audio: runtime-microfoonmachtiging en expliciete foreground-PTT, maximaal 60 s,
PCM mono 16 kHz. Geen ruwe audiofiles/cache/logs, geen achtergrondmicrofoon.
Audio gaat over het bestaande beveiligde kanaal naar eigen server; Whisper/Piper
blijven daar lokaal. Herkende tekst en chatcontext kunnen bij gekozen Groq/Gemini
naar de externe AI-provider gaan. Ollama houdt AI lokaal als die beschikbaar is.
Nieuwe speechroutes eisen expliciet chat:write/read, beoordelen WAV-formaat en
grootte, begrenzen parallelisme/rate en hercontroleren sessies na inference.

Alleen launcher-activity is exported; de FCM-service is niet exported.
Permissies: internet/netwerkstatus, expliciet record_audio en post_notifications.
FCM/WorkManager voegen de normale receive/boot/wake-lock- en eigen beschermde
receiverpermissies toe voor begrensde jobs. De ongebruikte foregroundservice en
bijbehorende permissie zijn expliciet uit het gemergde manifest verwijderd.
Geen contacten, SMS, telefonie, locatie, camera, always-on service of opslagrechten.
Push bevat alleen een categorie; de app toont uitsluitend vaste generieke tekst.
Geen externe link/actie of belactie uit pushpayloads. Alleen later mag urgent
een echte inkomende oproep kunnen veroorzaken; er bestaat nu geen beltransport.

Signing: debug wordt automatisch met een lokale Android-debugkey getekend.
De releaseconfig produceert een unsigned artefact; echte signinggegevens blijven
bij de eigenaar. Geen signing-wachtwoorden, google-services.json of keystores in Git.
