# Geprioriteerd verbeterplan

Uitgangspunt: eerst de bestaande ervaring samenhangend maken, binnen fase 7.5.
Zie ARCHITECTURE_REVIEW.md voor codebewijs en de volledige gap analysis.

## Eerste incrementele wijziging

1. Leg de ontvangen volledige visie vast en verbind AGENTS aan de vijf documenten.
2. Schrijf falende regressies voor verhalen met domeinwoorden, terugval met
   historie/stijl, oude taakvragen en tekst-/spraakconsistentie.
3. Herstel de verouderde basisprompt; geef gewone gesprekken ruimte, met dezelfde
   grenzen voor uitvoering, privacy en modelidentiteit.
4. Behoud de bestaande kandidaatselectie maar laat een domeinwoord alleen niet
   volstaan: een actuele vraag/opdracht of duidelijk gekoppeld vervolg is nodig.
   Voeg geen aparte classificatiemodelcall aan iedere beurt toe.
5. Laat een planner die 'chat' kiest via de bestaande ChatService-context en
   router streamen. Geen vaste functie-uitleg en geen tweede persoonlijkheid.
6. Bereken de route één keer; sluit alle persoonlijkheidswaarden op tekst én
   spraak aan. Houd gewone spreektekst buiten toolsamenvatting.
7. Draai bestaande security-/privacy-/toolregressies, 20/50-beurtcontracten,
   providerwissel en lokale synthetische modelmetingen. Meet grenzen eerlijk.
8. Publiceer de eigen diff als afhankelijke PR; geen automatische integratie van
   de nog open PR24/25/26 of gebruikerswijzigingen. Documenteer echte CI-uitkomst.

## Vervolgens, na bewijs per stap

| Prioriteit | Werk | Afhankelijkheid / stopcriterium |
|---|---|---|
| P1 | Algemene gesprek-naar-taakverwijzingen en hervatten van afhankelijke opdrachten | Brongebonden referenten, huidige expliciete intentie, één vraag bij ambiguïteit; nooit een model als approvalbron. |
| P1 | Fysieke turn-taking, focus, interruptie en echoacceptatie op beide clients | Bestaande microfoontoestemming; geen extra achtergrondrechten. |
| P1 | Echte einde-spraak-tot-audio- en CPU/GPU/RAM-profielen | Zelfde modellen/instellingen, koude én warme runs; geen mini-pc-conclusie zonder hardware. |
| P1 | Stemluistertest via Voice Studio | Bestaande Supertonic/Piper; favoriete stem niet automatisch vervangen. |
| P2 | Episodische/contactretrieval en lang gesprek | Eerst fouten uit H analyseren; geen ongerichte databasecontext of nieuw framework. |
| P2 | Planning met betrouwbare reistijd/voorbereiding en mailopvolging | Bestaande integraties/approval; afwezige bronnen niet verzinnen. |
| P2 | Relevante events als natuurlijke gesprekscontext | Opt-in categorieën, bron-ID, quiet hours, beperkte frequentie. |
| Roadmap | WhatsApp/Signal/SMS en nieuws | Beschikbare toegestane integraties, aparte machtigingen en platformbeoordeling. |
| Fase 8 | Android-internetoproepen/WebRTC/FCM | Aparte opdracht, Firebaseconfig en beveiligde signaling; nu niet implementeren. |
| Later | 24×7 en 8-GB-mini-pc | CPU/hardwaremeting, apart migratie-/deploymentbesluit; nu niet verplaatsen. |

Geen groot taalmodel, online TTS, modeldownload of betaalde dienst wordt als
stilzwijgende oplossing gekozen. Qwen2.5:3B blijft lokaal uitgangspunt; Gemini
gebruikt dezelfde toegestane gesprekscontext en persoonlijkheid. De bestaande
transportklasse wordt behouden. Na de echte 4096/6000-tokenmismatchmeting is
daarbinnen een headless opt-in voor native Ollama Chat toegevoegd, met expliciete
contextallocatie en afzonderlijke parser-/compatibiliteitstests. De bestaande
desktopcallers, Gemini en Groq blijven hun compatibele transport gebruiken.

## Eindrapport en status

Aan het einde worden implementatie, automatische bewijzen, echte modelkwaliteit,
metingen, niet-uitgevoerde hardware/accountproeven en resterende stappen apart
vastgelegd. Groene tests betekenen geen definitieve gebruikersacceptatie.

De uitgevoerde eerste verbetering en alle meet-/acceptatiegrenzen staan in
[EXPERIENCE_TEST_REPORT.md](EXPERIENCE_TEST_REPORT.md).
