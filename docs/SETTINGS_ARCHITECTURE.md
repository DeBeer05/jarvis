# Instellingenarchitectuur — fase 7.5 in uitvoering

De bestaande FastAPI-app bezit `NaturalService.settings`. Er is geen aparte
configuratieserver, database of credential store. `natural_settings` in dezelfde
SQLite-database bevat user_id, scope, device_id, revision, payload en updated.
Configuratieversie 1 gebruikt strikte geneste Pydantic-modellen en veilige defaults.

## Grenzen

- `user`: gedeelde gespreks-/persoonlijkheids-/AI-/geheugenvoorkeuren.
- `device`: uitsluitend het actuele eigen apparaat, geen willekeurig device_id.
- Serveradres, poort, bootstrap-eigenaar, certificaatregels en geheimen zijn
  geen normale gebruikersinstellingen. API-sleutels/OAuth-tokens blijven buiten
  deze tabel en algemene export.
- Windows bewaart daadwerkelijke hardwarekeuze/toestemming lokaal; Android
  gebruikt OS-machtigingen en eigen DataStore. Een serverwaarde opent geen microfoon.

Elke transactie controleert de levende authenticatiesessie en bepaalt user_id
uit de sessie, nooit uit de requestbody. Alle endpoints vallen onder de bestaande
default-deny gate en cookie-CSRF/native bearerregels. Persoonlijke leesinstellingen
gebruiken chat:read, wijzigingen chat:write. Automatiseringen houden hun afzonderlijke
actuele grants; instellingen kunnen bevoegdheden alleen beperken.

`revision` is verplicht bij opslaan/import/reset. `BEGIN IMMEDIATE` plus vergelijking
met de actuele versie voorkomt verloren wijzigingen. Een conflict geeft 409;
clients behouden hun invoer en moeten verversen. Audit bevat gebeurtenis/target,
geen configuratiewaarden of geheimen.

## API

Alle paden beginnen met `/api/v1/natural`:

| Pad | Methoden | Functie |
|---|---|---|
| `/settings/schema` | GET | 13 categorieën, labels, typen, grenzen, ondersteunde acties en geïnstalleerde voicekeuzes |
| `/settings` | GET, PUT | Globale versiegebonden voorkeuren |
| `/settings/{category}` | PATCH | Eén categorie wijzigen |
| `/settings/reset` | POST | Alle of één categorie herstellen |
| `/settings/export` | GET | Niet-geheime configuratieversie 1 |
| `/settings/import` | POST | Strikt gevalideerde export met actuele revision |
| `/device-settings` | GET, PUT | Alleen eigen apparaatscope |
| `/memory`, `/memory/search`, `/memory/{id}` | GET, POST, PUT, DELETE | Gebruikersgebonden geheugenbeheer |
| `/summaries`, `/summaries/{id}` | GET, PUT | Samenvattingen lezen/wijzigen met revision |
| `/tasks` | GET | Hervatbare taakreferenties; extra automation:read vereist |

Voicecapabilities gebruiken uitsluitend bestandenmetadata; geen modelimports,
downloads of geheime paden in antwoorden. Alleen bestaande Whisper Small/Base/Tiny
en Piper Ronnie/MLS worden aangeboden; ontbrekende keuzes staan uitgeschakeld.
XTTS/hybride/system-TTS wordt niet als beschikbare serverprovider voorgesteld.
Een gewijzigd model/stem moet geïnstalleerd zijn; CPU/GPU-status blijft onbewezen
tot de echte runtime een aanvraag heeft verwerkt.

## Clients en actuele implementatiegrens

Windows rendert types als passende Qt-controls, op de hoofdthread; API-werk draait
via bestaande workers. Android gebruikt Compose en de bestaande JarvisApi/OkHttp
op IO-coroutines. Beide bieden categorieën, zoeken, dirty-state, opslaan/annuleren,
reset, import/export en geheugen/samenvattingen. Instellingenwijzigingen verlenen
geen adminrechten en kunnen mandatory approvals niet uitschakelen.

Centrale opslag/UI zijn geïmplementeerd. De overige fase-7.5-audio-, intent-,
privacyretentie- en diagnostiekonderdelen worden nog aangesloten. Een opgeslagen
instellingenveld is op zichzelf geen bewijs dat iedere beschreven runtimefunctie
al beschikbaar is. Zie DEVELOPMENT_PROGRESS.md en het uiteindelijke testrapport.
