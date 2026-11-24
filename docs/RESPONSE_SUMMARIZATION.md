# Antwoorden samenvatten

Antwoordgedrag staat bij Gespreksinstellingen. Auto kiest doorgaans Kort voor spraak
en Gebalanceerd voor schriftelijke uitvoer. Het model krijgt eerst de directe vraag,
stijl en relevant geselecteerde context. Belangrijke informatie heeft voorrang op lengte.
Er is geen harde woordenknip. Technische budgetten en bronlimieten blijven begrensd.

‘Wat staat in mijn laatste tien mails?’ zoekt zelf de recente inboxberichten, leest
de inhoud van maximaal twintig berichten en maakt één gezamenlijke samenvatting.
JARVIS vraagt hiervoor geen bericht-ID's en geen tweede toestemming om te lezen;
de bestaande leesrechten en uitgeschakelde tools blijven gelden. Standaard worden
vijf recente berichten samengevat. ‘Lees de tiende mail’ gebruikt het geverifieerde
ID uit dezelfde chat. Er worden geen verzend-/wijzigingsopdrachten aangemaakt.
Bronselecties en ontbrekende volledige tekst worden vermeld. Een onbeschikbare
samenvatter geeft een duidelijk gemarkeerd lokaal inhoudsoverzicht als terugval.
Gevoelige inhoud gaat niet naar cloud-AI wanneer het privacybeleid dat verbiedt:
JARVIS gebruikt dan uitsluitend de bestaande lokale Ollama-route, zonder cloudretry.
Als samenvatten faalt, noemt het overzicht de oorzaak (bijvoorbeeld lokale AI niet
bereikbaar, quota, time-out of contextlimiet) naast het lokale inhoudsoverzicht.
Unicode blijft compact in het bronpakket; accenten en emoji vergroten het budget
niet kunstmatig door JSON-escapetekst.

Specifieke zoekfilters en verzoeken om alleen onderwerpen blijven op de bestaande
zoekroute: zulke overzichten benoemen de opgehaalde hoeveelheid en mogelijke relevante
onderwerpen en zeggen wanneer de inhoud nog niet is gelezen. Een mail met alleen
onderwerp is niet bewezen belangrijk of urgent. Individuele gelezen mail wordt extractief samengevat, met
extra behoud van regels over deadlines, waarschuwingen, fouten, kosten en onzekerheid.
Dit is een heuristiek: een ingewikkelde impliciete deadline kan aanvullende lezing vergen.

Agenda-overzichten geven aantal, eerste afspraak en gedetecteerde overlap. Ze claimen
geen vrije uren, betrouwbare reistijd of volledige agenda bij een begrensde zoekselectie.
'Welke afspraken heb ik?' en expliciet volledig voorlezen mogen een opsomming geven.

'Wat staat er in die sollicitatie?' zoekt een uniek onderwerp in de geverifieerde
berichtlijst. 'Vertel meer', 'Lees alles voor' en andere vervolgvragen gebruiken het
laatst besproken bericht-ID. Bij meerdere matches vraagt JARVIS welke mail bedoeld is.
De echte leestool controleert opnieuw rechten. Ontvangen tekst wordt nooit een opdracht.

Goedkeuringsvoorstellen worden volledig weergegeven en uitgesproken, met behoud van
ontvanger, onderwerp, inhoud, tijden, genodigden en gevolgen. Opmaak en technische
voorstel-ID's hoeven niet te worden uitgesproken. Een stijlprofiel kan geen ja geven.
