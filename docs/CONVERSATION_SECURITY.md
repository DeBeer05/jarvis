# Gespreksbeveiliging — fase 7.5

Alle persoonlijke routes gebruiken bestaande authenticatie, apparaatmachtigingen,
loopback-/hostcontrole en bij cookies CSRF. Instellingen kunnen die controles,
TLS-validatie of verplichte externe goedkeuring niet uitschakelen. Niet-loopback
native verbindingen vereisen HTTPS. Android-debug gebruikt alleen vaste lokale
hosts en expliciete adb reverse. Er is geen publiek geopende poort.

## Autoriteit

De huidige gebruikersinstructie, niet het modelantwoord, bepaalt de toegestane
actiedomeinen. Plannen en parameters gebruiken gesloten Pydantic-schema's.
Ontvangen e-mail, afspraken, documenten, voorkeuren en eigen persoonlijkheidstekst
zijn onbetrouwbare gegevens. Er wordt geen modelcode, shell of willekeurige plugin
uitgevoerd. Apparaatrechten en blokkades worden bij planning, indienen en vóór een
externe wijziging opnieuw gecontroleerd.

Een gesproken/getypte bevestiging bindt aan het laatste volledige ongewijzigde
servervoorstel in dezelfde sessie/apparaat/chat, payloadfingerprint en vervaltijd.
De AI ontvangt geen approvalnonce en kan niet goedkeuren. Meerdere voorstellen
vereisen een specifieke selectie. Correcties maken een nieuw voorstel; een oude
ja kan dat niet automatisch autoriseren. Een onderbreking van spraak is geen
terugdraaien van een verzonden mail of andere uitgevoerde externe actie.

## Audio

Microfoon bij opstart uit; lokaal onthouden toestemming vervangt bewuste activatie
niet. Doorloop blijft begrensd door voorgrond/timeouts/Stop alles. Barge-in is opt-in,
heeft echo-/transcriptguards en negeert late callbacks. Audio blijft in begrensde
buffers en wordt niet standaard op schijf of in de gebruikersdatabase opgeslagen.
Disconnect/intrekking stopt de eigen inference en laat andere processen ongemoeid.

De microfoon verifieert geen persoonlijke stemidentiteit. Andere mensen in de
ruimte en moeilijke akoestiek zijn daarmee hardware-/gebruiksgrenzen, geen
bewezen biometrische beveiliging. Android vereist voor duplex beschikbare en
actieve platform-AEC. Windows heeft een lichte referentiefilter; dat is geen
garantie voor alle luidsprekers/reflecties. Echte audioacceptatie blijft vereist.

## Geheugen en diagnostiek

Geheugen/instellingen/taakcontext zijn gebruikersgebonden. Gevoelige herinneringen
vereisen expliciete toestemming en blijven buiten cloudcontext. Geheimen worden
geweigerd; API-sleutels/OAuth blijven in de bestaande secretstore. Offline forceert
lokale AI, ook voor interne planners/samenvattingen. Vergeten invalideert bronnen,
afgeleide context en samenvattingen. Oude backups/originele gesprekken hebben een
afzonderlijke levenscyclus; zie de geheugenhandleiding.

Diagnostiek accepteert alleen begrensde numerieke events en vaste foutcodes.
Geen prompts/transcripties/geheugeninhoud, vrije fouttekst of credentials in export.
De optionele GPU-probe gebruikt vaste lokale argumenten met deadline/cache en geen
modelinvoer. Beveiligingsheaders gebruiken pure ASGI om disconnect niet te maskeren.

Tests dekken onder meer intrekking, ontbrekende rechten, bronbinding, externe
prompt-injection, gewijzigde/verlopen previews, dubbel uitvoeren en apparaatsovername.
Testresultaten en handmatige hardwareacceptatie moeten afzonderlijk worden gelezen.
