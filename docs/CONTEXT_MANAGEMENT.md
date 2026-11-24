# Contextbeheer — fase 7.5

De bestaande ChatService roept één ContextManager aan. Gemini, Groq en Ollama
ontvangen dezelfde structuur; providerkeuze en offlinebeleid blijven request-local.
Er is geen tweede router en geen database-export naar een model.

## Selectie en budget

Context bevat de vaste systeemregels, bij spraak een afzonderlijke spreekprompt,
actuele datum/tijd/tijdzone, aanspreekvoorkeuren, relevante herinneringen, een
eventuele samenvatting, recente complete berichtparen en beperkte taakstatussen.
Taakstatus verleent geen uitvoeringsrecht. Goedkeuringsparameters/nonces blijven
bij Automation/ApprovalManager, buiten gewone modelsamenvattingen.

Het tokenbudget gebruikt conservatief UTF-8-bytes/3 als schatting, plus de bestaande
tekenlimiet. Dit is geen provider-tokenizer of kostenmeting. Het huidige bericht en
de systeemregels mogen niet worden afgekapt. Minder belangrijke context wordt per
volledig item verwijderd. Bij een te klein budget wordt de beurt veilig afgewezen.

Recente paren blijven intact. Een onderbroken antwoord wordt als onderbroken
gemarkeerd en vormt geen bewijs van taakuitvoering. Een lange geschiedenis wordt
lokaal extractief samengevat; de laatste beurten blijven daarnaast beschikbaar.
Alleen gebruikerszinnen worden nu extractief opgenomen, geen verzonnen conclusies.
Volledigere semantische samenvattingen zijn nog in uitvoering.

## Privacy

Langetermijngeheugen gaat standaard alleen naar een uitsluitend lokale AI-route.
Gewone herinneringen naar cloud vereisen opt-in; gevoelige herinneringen blijven
lokaal en vereisen een afzonderlijke instelling. Gevoelige eerdere gebruikers- én
assistenttekst en bewerkte gevoelige samenvattingen worden uit cloudcontext geweerd.
Deze woorddetectie is een extra filter, geen volledige classificatie van alle
mogelijke persoonsgegevens. Een bewust verzonden huidige cloudvraag blijft een
cloudvraag; offline voorkomt alle cloud-AI-aanroepen, ook interne planning.

Bij geschiedenis uit schrijft de server vanaf de nieuwe beurt geen gewone
gebruikers-/antwoordtekst naar SQLite. De actieve context blijft begrensd in RAM:
maximaal 50 gesprekken, 20 beurten en 32.000 tekens per gesprek, met eigen
inactiviteitsverval. Een herstart wist die tijdelijke context. Metagegevens voor
request-idempotentie blijven bestaan. Openstaande taken houden noodzakelijke
taakparameters apart; expliciet onthouden blijft een afzonderlijke keuze.

Eerdere opgeslagen gesprekken worden door uitschakelen niet achteraf verwijderd.
De ingestelde geschiedenisbewaartermijn ruimt oude inhoud op; handmatig verwijderen
blijft beschikbaar. Android stopt offline caching wanneer geschiedenis uit staat
en wist de oude versleutelde Room-cache voor die server.

## Vergeten en wijzigingen

Herinneringen koppelen aan hun bronbeurt en aan beurten die ze als context gebruikten.
Vergeten sluit die bronnen en afgeleide antwoorden uit van nieuwe AI-context,
verwijdert FTS-items en invalideert samenvattingen. Bij een geheugenwijziging stopt
een lopende gewone generatie die van de oude versie uitgaat. Native TTS-caches
worden bij geheugenbeheerwijzigingen gewist.

Samenvattinginvalidatie is momenteel conservatief: ook andere samenvattingen van
dezelfde gebruiker kunnen worden verwijderd om herintroductie te voorkomen.
Het oorspronkelijke gesprek blijft afzonderlijk bestaan tot expliciete verwijdering
of retentie. Deze grenzen worden ook in geheugenbeheer uitgelegd.
