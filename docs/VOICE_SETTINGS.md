# Antwoord- en steminstellingen

Antwoordgedrag bevat profielen Automatisch, Dagelijks gesprek, Technische uitleg, Korte briefing en Aangepast, naast zes modi, gesproken/geschreven lengte, samenvatten, progressive
disclosure, detail-/achtergrondniveau, herhaling en nuttige vervolgvragen, plus voorkeuren
voor mail/agenda/nieuws/berichten. De hoofdmodus Auto gebruikt de aparte kanaalkeuze.
Algemene antwoorden worden in de oorspronkelijke AI-aanroep gestuurd; toolspraak gebruikt
begrensde lokale extractie. Essentiële informatie en goedkeuringen blijven beschermd.

Stem en audio bevat Automatic/Quality/Fast/Offline/Manual, configuratieprofiel, geïnstalleerde
provider/stem, snelheid, volume, kwaliteitsstappen, pauze, streaming per zin, caching,
fallback en het bestaande vrijgeven na inactiviteit. Automatic is lokaal; offline kan
geen netwerkprovider selecteren. Whisper CPU/GPU-keuze verandert de TTS-CPU-backend niet.

Voorbeelden van gesloten gesproken instellingenopdrachten:
- Geef voortaan kortere antwoorden.
- Je hoeft niet alles voor te lezen.
- Vat mijn e-mails voortaan samen.
- Geef bij technische vragen meer uitleg.
- Praat iets langzamer / Praat iets sneller.
- Gebruik wat minder sarcasme.
- Je hoeft me geen meneer te noemen.
- Schakel over naar offline spraak.
- Gebruik de Classic Butler-stem.

'Voortaan', 'permanent' of 'vanaf nu' bewaart via dezelfde SettingsManager-validatie en
revisiecontrole. Zonder die woorden geldt het tijdelijk voor deze sessie/apparaat/chat,
maximaal 30 minuten; niet na serverherstart. Tijdelijke instellingen kunnen geen rechten,
privacytoestemming of veiligheidsbeleid veranderen. Alleen exact herkende opdrachten
worden lokaal toegepast. Voor diepere stem: kies en beluister een vaste stem in Studio;
onbeschikbare toonhoogte wordt niet gefingeerd. Standaardwaarden herstellen blijft de
bestaande veilige API gebruiken. Nieuwe velden zijn additief; SQLite-schema blijft 7.
