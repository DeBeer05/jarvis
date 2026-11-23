# Android-meldingen en FCM

Vier echte Android-kanalen: **urgent**, **appointments**, **important**, **news**.
Urgent heeft hoge importance, overige standaardimportance; Android/gebruiker
kan kanaalgedrag overschrijven. De app toont altijd generieke inhoud en gebruikt
VISIBILITY_PRIVATE, een immutable PendingIntent en uitsluitend eigen navigatie.

Bij Meldingen: geef op Android 13+ toestemming, selecteer categorieën en kies
Test. Dit is een echte lokale Android-notificatie, geen FCM-bezorging. Een
geweigerde permissie leidt niet tot een crash. Uitschakelen van FCM beëindigt
auto-init, annuleert registratie-WorkManager en verwijdert de pending token.

Optionele Firebaseclient gebruikt firebase-messaging, zonder hardcoded project.
Geef voor je eigen Android-appregistratie bij een eigen build Gradleproperties:
firebaseAppId, firebaseProjectId, firebaseApiKey, firebaseSenderId. Bewaar lokale
configuratie buiten Git; deel geen service-accountcredentials in chat of APK.
De build genereert alleen de benodigde publieke clientresources als je de
configuratie bewust opgeeft. Auto-init staat standaard uit, ook met configuratie.

Na expliciet inschakelen: onNewToken slaat de token tijdelijk versleuteld op en
WorkManager registreert hem bij het eigen apparaat via de bestaande bearer-auth.
Netwerkconstraint, exponentiële backoff en maximaal vier retries begrenzen werk;
geen permanente polling. De backend bewaart in deze fase uitsluitend een digest
en categorieën, maximaal 64 registraties in RAM, en meldt eerlijk
`external_delivery_available=false`. Ontkoppelen verwijdert de eigen registratie.

**Nog nodig voor echte externe push:** eigen Firebase-project/appconfiguratie,
server-side beveiligde FCM-credentialstore en deliveryadapter met reversibel
beveiligde tokenopslag, configuratie van de vertrouwde toegangspoort, en een echte
end-to-end-FCM-proef op een geschikte telefoon/emulator met Google Play Services.
Die credentials zijn hier niet aangeleverd. Geen externe pushbezorging geclaimd.
De lokale testimplementatie werkt zonder Google-account of productiegebeurtenissen.

Firebase kan later een gesloten appproces wekken; lifecycle-/servicearchitectuur
is daarvoor voorbereid. Er is nu geen eventbron uit fase 7, geen oproep-FCM of
WebRTC/Telecom. Alleen urgent mag later automatisch een oproep aankondigen.
