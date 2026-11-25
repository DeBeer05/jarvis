# Gebruikerservaring — verifieerbare eisen

Bron: JARVIS_MASTER_VISION.md. Deze eisen gelden voor toekomstige fasen; ze
verlenen geen extra rechten of fasevrijgave.

| ID | Eis | Waarneembaar criterium |
|---|---|---|
| UX01 | Gesprek is de standaard | Verhalen/grappen/meningen, ook over mail of afspraken, veroorzaken geen automatische persoonlijke read/write. |
| UX02 | Geen functiemodus nodig | Van praten naar een expliciete ondersteunde opdracht in dezelfde conversation_id. |
| UX03 | Context behouden | Recente beurten en relevante herinneringen blijven beschikbaar bij onderwerp- en modelwissel; budget en privacy blijven gelden. |
| UX04 | Gerichte verduidelijking | Vraag alleen ontbrekende gegevens; oude taakvragen trekken een nieuw onderwerp niet naar zich toe. |
| UX05 | Eén persoonlijkheid | Instellingen gelden voor tekst en spraak en bij terugval uit toolplanning. Geen vaste begroeting/afsluitvraag. |
| UX06 | Situationele lengte | Reageer op een verhaal of grap; samenvatten alleen waar zinvol. Noodzakelijke uitleg en risico's blijven intact. |
| UX07 | Betrouwbaar handelen | Alleen backendbewijs bevestigt uitvoering; een voorstel of concept is geen verzonden bericht. |
| UX08 | Onderbreken | Oude audio/generatie stopt; correctie blijft gesprekstekst, uitgevoerde taken worden niet verzwegen. |
| UX09 | Rustige beurtwisseling | Een korte denkpauze beëindigt geen halve zin; zichtbaar luisteren, Stop werkt, eigen TTS wordt geen opdracht/ja. |
| UX10 | Controle over geheugen | Inzien/corrigeren/vergeten, relevante selectie en geen gevoelige cloudcontext zonder bestaande toestemming. |
| UX11 | Gecontroleerde proactiviteit | Alleen herleidbare echte/gesimuleerde events, categorie/quiet hours/limieten; melding blijft bespreekbaar. |
| UX12 | Eerlijke mogelijkheden | Niet-gekoppelde of toekomstige integraties worden niet als beschikbaar gepresenteerd. |
| UX13 | Instellingen hebben effect | Globale voorkeuren synchroniseren; hardware/OS-toestemming blijft per apparaat. |
| UX14 | Gebruiker accepteert ervaring | Automatische contracttests en menselijke luister-/gespreksscores worden afzonderlijk gerapporteerd. |

Meet per scenario: ontbrekende/verkeerde referenties, onnodige vragen, herhaling,
onjuiste uitvoeringsclaims, ongewenste samenvatting en stijlverlies. Noteer
latency met een duidelijk begin/eindpunt. De veiligheidslimieten op context,
output, audio en concurrency blijven; dat zijn geen productregels die elk
antwoord onnatuurlijk kort moeten maken.
