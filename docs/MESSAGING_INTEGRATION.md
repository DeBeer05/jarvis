# Berichten en nieuws

MessagingProvider is een kleine interface. De huidige veilige adapter is
ManualMessagingProvider: ontvanger en tekst opstellen/tonen, daarna handmatig
delen via de Android-sharechooser. sent=false en reply_tracking=false blijven
expliciet in het resultaat. De gebruiker kiest de app/ontvanger en verstuurt zelf.
POST /api/v1/automation/manual-message bereidt dit resultaat voor.

De officiële WhatsApp Cloud API is een Business-integratie met eigen
business-/telefoonregistratie en voorwaarden. Die is niet ingericht voor jouw
persoonlijke WhatsApp-account. Er wordt geen WhatsApp Web gescrapet, sessie
overgenomen of verzend-/leesmogelijkheid geclaimd. Zie
[Meta Business phone registration](https://developers.facebook.com/docs/graph-api/reference/whats-app-business-account-to-number-current-status/register/).

SMS is eveneens een toekomstige geautoriseerde provider; deze versie vraagt
geen Android-SMS-rechten en leest/verstuurt geen SMS. E-mail gebruikt uitsluitend
de in GMAIL_INTEGRATION beschreven goedkeuringsroute.

Voor een verzoek over een afspraak: zoek eerst de exacte afspraak/contactgegevens,
stel een bericht op, controleer ontvanger/inhoud en kies Gmail of handmatig delen.
Alleen Gmail heeft hier verifieerbare thread-follow-ups. Bij handmatig delen
wordt geen antwoordherkenning of agenda-akkoord verzonnen. De agenda blijft
ongewijzigd tot een afzonderlijk gecontroleerd wijzigingsvoorstel is goedgekeurd.

NewsProvider is optioneel als interface voorbereid. Er is geen nieuwsbron,
scraper of automatische nieuwscontrole actief; er worden geen onbevestigde
nieuwsfeiten of realtime-dekking geclaimd. Voor een latere adapter moeten bron,
voorwaarden, rate limits en gebruikersinteresses expliciet worden ingericht.
