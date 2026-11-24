# Voice Studio gebruiken

Windows: Instellingen → Gesprekken en geheugen → Voice Studio.
Android: Instellingen → Gesprekken en geheugen → Voice Studio (build 708 of nieuwer).
Kies Stemmen ophalen, een geïnstalleerde stem en een voorbeeldtekst (1–350 tekens).
Stel snelheid en volume in, kies Beluisteren of Vergelijk achter elkaar. Vergelijking
is serieel; Stop onderbreekt uitvoer/generatie. Er wordt geen microfoon geopend.

Dezelfde zes Nederlandse testzinnen staan in scripts/benchmark_tts.py. Gebruik dezelfde
tekst bij het vergelijken. Gegevens tonen de werkelijk gekozen provider, stem, tijd tot
het volledige eerste zinsbuffer en helper-RAM. Het is geen meting van akoestische output
op de luidspreker of totale AI-responstijd. CPU/GPU-systeemmetingen staan bij Diagnostiek.

Als favoriete stem opslaan bewaart provider, stem, handmatige modus, snelheid en volume
via de bestaande versiecontrole. Overige bewerkte instellingen eerst opslaan/annuleren.
Globale voorkeuren synchroniseren; lokale microfoon/luidspreker blijven op het apparaat.
Andere profielen kies je bij Stem en audio; Classic Butler-persoonlijkheid apart.

Ondersteund: snelheid, volume, Piper MLS-sprekernummer, Supertonic inferentiestappen en
pauze tussen tekstblokken. Niet ondersteund: vrije pitch, emotie-/expressiviteitsregelaar,
GPU-TTS of onlineproviders. Die worden niet als werkende Studio-regelaars getoond.
Luister zelf naar M1–M5; 'beste' natuurlijkheid, warmte en diepte zijn nog niet beoordeeld.
