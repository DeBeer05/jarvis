package nl.jarvis.mobile

import android.Manifest
import android.os.Build
import android.os.Bundle
import android.content.Intent
import android.net.Uri
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.launch
import nl.jarvis.mobile.features.*
import nl.jarvis.mobile.data.Preferences

class MainActivity: ComponentActivity() {
    private val model: JarvisViewModel by viewModels()
    private val microphone = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted -> if(granted) model.ptt() else model.message("Microfoontoestemming geweigerd; je kunt blijven typen") }
    private val notifications = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted -> if(!granted) model.message("Meldingen staan uit in Android") }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val state by model.state.collectAsStateWithLifecycle()
            JarvisTheme(state.preferences.theme) { JarvisApp(state, model,
                mic={ microphone.launch(Manifest.permission.RECORD_AUDIO) },
                notificationPermission={ if(Build.VERSION.SDK_INT>=33) notifications.launch(Manifest.permission.POST_NOTIFICATIONS) }) }
        }
        intent?.getStringExtra("screen")?.let(model::navigate)
    }
    override fun onStart() { super.onStart(); model.active(true) }
    override fun onStop() { model.active(false); super.onStop() }
    override fun onNewIntent(intent: Intent) { super.onNewIntent(intent); intent.getStringExtra("screen")?.let(model::navigate) }
}

@Composable fun JarvisTheme(theme: String, content: @Composable () -> Unit) {
    val dark=theme=="dark" || (theme=="system" && isSystemInDarkTheme())
    val colors=if(dark) darkColorScheme(primary=Color(0xFF71DBBD), background=Color(0xFF10171D), surface=Color(0xFF151F27), surfaceContainer=Color(0xFF1C2A33))
        else lightColorScheme(primary=Color(0xFF166B57))
    MaterialTheme(colorScheme=colors, content=content)
}
private val screens=listOf("Welkom","Inloggen","Koppelen","Chat","Gesprekken","Spraak","Automatiseringen","Meldingen","Apparaten","Instellingen","Account")
private fun navigationTitle(screen: String, language: String): String = if(language!="en") screen else mapOf(
    "Welkom" to "Welcome", "Inloggen" to "Sign in", "Koppelen" to "Pair device", "Gesprekken" to "Conversations",
    "Spraak" to "Voice", "Meldingen" to "Notifications", "Apparaten" to "Devices", "Instellingen" to "Settings"
)[screen] ?: screen

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun JarvisApp(state: ScreenState, model: JarvisViewModel, mic: () -> Unit, notificationPermission: () -> Unit) {
    val drawer=rememberDrawerState(DrawerValue.Closed); val scope=rememberCoroutineScope()
    ModalNavigationDrawer(drawerState=drawer, drawerContent={ ModalDrawerSheet {
        Text("J A R V I S", Modifier.padding(24.dp), style=MaterialTheme.typography.headlineMedium, color=MaterialTheme.colorScheme.primary)
        Column(Modifier.verticalScroll(rememberScrollState())) { screens.forEach { screen ->
            NavigationDrawerItem(label={Text(navigationTitle(screen,state.preferences.language))}, selected=state.screen==screen, onClick={model.navigate(screen); scope.launch { drawer.close() }}, modifier=Modifier.padding(horizontal=12.dp))
        } }
    } }) {
        Scaffold(topBar={ TopAppBar(title={ Text("JARVIS · ${navigationTitle(state.screen,state.preferences.language)}", fontWeight=FontWeight.SemiBold) }, navigationIcon={ TextButton(onClick={scope.launch {drawer.open()}}) {Text("☰", style=MaterialTheme.typography.headlineSmall)} },
            actions={ TextButton(onClick=model::reconnect) { Text(if(state.connection.authenticated) "● Online" else if(state.connection.online) "○ Inloggen" else "○ Offline") } }) }) { padding ->
            Column(Modifier.fillMaxSize().padding(padding).imePadding().widthIn(max=1100.dp).padding(horizontal=20.dp, vertical=8.dp)) {
                if(state.error.isNotBlank()) Surface(color=MaterialTheme.colorScheme.errorContainer, shape=MaterialTheme.shapes.medium, modifier=Modifier.fillMaxWidth().padding(bottom=12.dp)) {
                    Text(state.error, Modifier.padding(14.dp), color=MaterialTheme.colorScheme.onErrorContainer)
                }
                when(state.screen) {
                    "Chat" -> Chat(state,model)
                    "Spraak" -> Voice(state,model,mic)
                    else -> Column(Modifier.verticalScroll(rememberScrollState()).fillMaxWidth(), verticalArrangement=Arrangement.spacedBy(16.dp)) {
                        when(state.screen) {
                            "Welkom" -> Welcome(state,model)
                            "Inloggen" -> Login(state,model)
                            "Koppelen" -> Pairing(state,model)
                            "Gesprekken" -> History(state,model)
                            "Meldingen" -> NotificationSettings(state,model,notificationPermission)
                            "Apparaten", "Account" -> Account(state,model)
                            "Instellingen" -> Settings(state,model)
                            "Automatiseringen" -> AutomationScreen(state,model)
                        }
                        Spacer(Modifier.height(24.dp))
                    }
                }
            }
        }
    }
}
@Composable private fun Welcome(state: ScreenState, model: JarvisViewModel) {
    var origin by remember(state.preferences.origin) { mutableStateOf(state.preferences.origin) }
    Text("Jouw assistent,\nbinnen handbereik.", style=MaterialTheme.typography.headlineLarge)
    Text("Chat en praat met dezelfde JARVIS op je computer. Je gesprekken blijven centraal op jouw server.")
    OutlinedTextField(origin,{origin=it},label={Text("Vertrouwd serveradres")}, singleLine=true,modifier=Modifier.fillMaxWidth().testTag("serverAddress"))
    Text("Lokale ontwikkeling: verbind via USB/ADB met 127.0.0.1:8765. Voor wifi of extern gebruik is een expliciet vertrouwd HTTPS-endpoint nodig.", style=MaterialTheme.typography.bodySmall)
    Button(onClick={model.save(state.preferences.copy(origin=origin)); model.navigate("Inloggen")},modifier=Modifier.fillMaxWidth()) {Text("Verbinden")}
}
@Composable private fun Login(state: ScreenState, model: JarvisViewModel) {
    var user by remember { mutableStateOf("") }; var password by remember { mutableStateOf("") }
    Text("Welkom terug",style=MaterialTheme.typography.headlineMedium)
    Text("Log in en keur je Android-apparaat eenmalig goed als eigenaar. Daarna blijft je sessie veilig bewaard.")
    OutlinedTextField(user,{user=it},label={Text("Gebruikersnaam")},singleLine=true,modifier=Modifier.fillMaxWidth().testTag("username"))
    OutlinedTextField(password,{password=it},label={Text("Wachtwoord")},singleLine=true,visualTransformation=PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth().testTag("password"))
    Button(enabled=state.connection.online && user.isNotBlank() && password.isNotBlank(),onClick={val u=user;val p=password;password="";model.beginPair(u,p)},modifier=Modifier.fillMaxWidth()) {Text("Inloggen en koppelen")}
    TextButton(onClick={password="";model.beginPair()},enabled=state.connection.online) {Text("Koppelen met eigenaarcode")}
}
@Composable private fun Pairing(state: ScreenState, model: JarvisViewModel) {
    Text("Dit is jouw apparaat",style=MaterialTheme.typography.headlineMedium)
    if(state.pairCode.isBlank()) {
        Text("Vraag een koppelcode aan en bevestig die op je computer.")
        Button(onClick={model.beginPair()},enabled=state.connection.online) {Text("Koppelcode aanvragen")}
    } else {
        Text("Vergelijk deze code in de eigenaarinterface op je computer:")
        SelectionContainer {Text(state.pairCode,style=MaterialTheme.typography.displaySmall,color=MaterialTheme.colorScheme.primary,modifier=Modifier.testTag("pairCode"))}
        Text("Open op je computer de beveiligingspagina van JARVIS, controleer apparaatnaam en rechten en keur dit verzoek goed. De app rondt het koppelen automatisch af.")
        Text(state.pairUrl,style=MaterialTheme.typography.bodySmall)
    }
}
@Composable private fun ColumnScope.Chat(state: ScreenState, model: JarvisViewModel) {
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
        Text(state.model.ifBlank{"Een nieuw perspectief begint hier"},modifier=Modifier.weight(1f),style=MaterialTheme.typography.labelMedium)
        TextButton(onClick=model::newConversation,enabled=!state.busy){Text("＋ Nieuw")}
    }
    Row(horizontalArrangement=Arrangement.spacedBy(6.dp),modifier=Modifier.horizontalScroll(rememberScrollState())) { listOf("auto","groq","gemini","ollama").forEach {provider ->
        FilterChip(selected=state.provider==provider,onClick={model.provider(provider)},label={Text(provider.replaceFirstChar{it.uppercase()})})
    } }
    LazyColumn(Modifier.weight(1f).fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(14.dp)) {
        if(state.messages.isEmpty()) item {Text("Waar wil je vandaag aan werken?",Modifier.padding(vertical=28.dp),style=MaterialTheme.typography.headlineSmall)}
        items(state.messages) {line -> Surface(shape=MaterialTheme.shapes.large,color=if(line.role=="JIJ") MaterialTheme.colorScheme.surfaceContainer else MaterialTheme.colorScheme.surface,modifier=Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp)) {Text(line.role,style=MaterialTheme.typography.labelMedium,color=MaterialTheme.colorScheme.primary); Spacer(Modifier.height(8.dp)); SelectionContainer {Text(line.text.ifBlank{"…"})} }
        } }
    }
    var text by remember {mutableStateOf("")}
    OutlinedTextField(text,{if(it.length<=8000)text=it},placeholder={Text("Je bericht…")},maxLines=4,modifier=Modifier.fillMaxWidth().testTag("composer"))
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp)) {
        OutlinedButton(onClick={model.navigate("Spraak")}) {Text("Spraak")}
        if(state.busy) Button(onClick=model::stop,modifier=Modifier.weight(1f)){Text("Stop antwoord")}
        else Button(onClick={val value=text;text="";model.send(value)},enabled=state.connection.authenticated && "chat:write" in state.connection.permissions && text.isNotBlank(),modifier=Modifier.weight(1f).testTag("send")){Text("Versturen →")}
    }
}
@Composable private fun ColumnScope.Voice(state: ScreenState, model: JarvisViewModel, mic: () -> Unit) {
    val color by animateColorAsState(if(state.recording) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface)
    Text(state.voiceStatus,style=MaterialTheme.typography.headlineMedium,color=color)
    Text(if(state.recording) "Microfoon actief" else "Microfoon uit",style=MaterialTheme.typography.labelLarge)
    LinearProgressIndicator(progress={state.level},modifier=Modifier.fillMaxWidth().padding(vertical=16.dp))
    Button(onClick={if(state.recording)model.ptt()else mic()},enabled=state.connection.authenticated && "chat:write" in state.connection.permissions,modifier=Modifier.fillMaxWidth().heightIn(min=64.dp)) {Text(if(state.recording)"Opname afronden" else "Start luisteren")}
    Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) { OutlinedButton(onClick=model::stop) {Text("Stop alles")}; TextButton(onClick=model::sample,enabled=state.connection.authenticated && "chat:read" in state.connection.permissions){Text("Stemvoorbeeld")} }
    Text("JIJ",color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.labelSmall)
    SelectionContainer {Text(state.transcript.ifBlank{"Wat ik heb verstaan…"},Modifier.padding(vertical=12.dp))}
    HorizontalDivider()
    LazyColumn(Modifier.weight(1f).fillMaxWidth()) {item {SelectionContainer {Text(state.messages.lastOrNull{it.role=="JARVIS"}?.text ?: "Mijn antwoord…",Modifier.padding(vertical=16.dp))}}}
    Text("Push-to-talk werkt op de voorgrond. Achtergrond-wakeword en internetoproepen zijn nog niet beschikbaar.",style=MaterialTheme.typography.bodySmall)
}
@Composable private fun History(state: ScreenState,model: JarvisViewModel) {
    var deleting by remember {mutableStateOf<String?>(null)}
    Text(if(state.connection.online) "Je gesprekken" else "Lokaal versleutelde geschiedenis",style=MaterialTheme.typography.headlineMedium)
    TextButton(onClick=model::history){Text("Vernieuwen")}
    state.history.forEach {item -> Card(Modifier.fillMaxWidth()) {Row(Modifier.padding(12.dp),verticalAlignment=Alignment.CenterVertically) {
        TextButton(onClick={model.open(item.id)},modifier=Modifier.weight(1f)){Text(item.title)}
        TextButton(onClick={deleting=item.id},enabled=state.connection.authenticated && "chat:delete" in state.connection.permissions){Text("Verwijder")}
    } } }
    if(deleting!=null) AlertDialog(onDismissRequest={deleting=null},title={Text("Gesprek verwijderen?")},text={Text("Dit verwijdert het gesprek ook op de server en je andere apparaten.")},
        confirmButton={TextButton(onClick={deleting?.let(model::delete);deleting=null}){Text("Verwijderen")}},dismissButton={TextButton(onClick={deleting=null}){Text("Annuleren")}})
}
@Composable private fun NotificationSettings(state: ScreenState,model: JarvisViewModel,permission:()->Unit) {
    Text("Meldingen op jouw manier",style=MaterialTheme.typography.headlineMedium)
    Text(state.notificationStatus)
    OutlinedButton(onClick=permission){Text("Android-meldingen toestaan")}
    state.preferences.let {pref -> listOf("urgent","appointments","important","news").forEach {category ->
        Row(verticalAlignment=Alignment.CenterVertically) {Checkbox(checked=category in pref.categories,onCheckedChange={checked ->model.save(pref.copy(categories=if(checked) pref.categories+category else pref.categories-category))});Text(category,Modifier.weight(1f));TextButton(onClick={model.testNotification(category)}){Text("Test")}}
    } }
    Row(verticalAlignment=Alignment.CenterVertically) {Switch(checked=state.preferences.firebaseEnabled,onCheckedChange=model::firebase);Text("FCM inschakelen",Modifier.padding(start=12.dp))}
    Text("Zonder eigen Firebase-configuratie zijn alleen lokale voorbeeldmeldingen beschikbaar. Externe bezorging is nog niet geverifieerd.",style=MaterialTheme.typography.bodySmall)
}
@Composable private fun Account(state: ScreenState,model: JarvisViewModel) {
    var confirm by remember {mutableStateOf(false)}
    Text("Jouw Android-apparaat",style=MaterialTheme.typography.headlineMedium)
    SelectionContainer {Text(state.device)}
    Text("Andere apparaten beheer je als eigenaar via de beveiligingspagina op je computer.")
    OutlinedButton(onClick={model.logout()},enabled=state.connection.authenticated){Text("Uitloggen")}
    TextButton(onClick={confirm=true},enabled=state.connection.authenticated){Text("Dit apparaat intrekken")}
    if(confirm) AlertDialog(onDismissRequest={confirm=false},title={Text("Koppeling intrekken?")},text={Text("Je moet dit apparaat daarna opnieuw goedkeuren.")},confirmButton={TextButton(onClick={confirm=false;model.logout(true)}){Text("Intrekken")}},dismissButton={TextButton(onClick={confirm=false}){Text("Annuleren")}})
}
@Composable private fun Settings(state: ScreenState,model: JarvisViewModel) {
    var origin by remember(state.preferences.origin){mutableStateOf(state.preferences.origin)}
    val pref=state.preferences
    Text("Jouw werkruimte",style=MaterialTheme.typography.headlineMedium)
    OutlinedTextField(origin,{origin=it},label={Text("Serveradres")},singleLine=true,modifier=Modifier.fillMaxWidth())
    Button(onClick={model.save(pref.copy(origin=origin))}){Text("Serverprofiel opslaan")}
    Text("Sessies zijn aan dit exacte adres gebonden. Wisselen kan opnieuw koppelen vereisen.",style=MaterialTheme.typography.bodySmall)
    Row(verticalAlignment=Alignment.CenterVertically){Switch(pref.automatic,{model.save(pref.copy(automatic=it))});Text("Automatisch verbinden",Modifier.padding(start=12.dp))}
    Text("Thema")
    Row { listOf("dark","light","system").forEach {value ->FilterChip(selected=pref.theme==value,onClick={model.save(pref.copy(theme=value))},label={Text(when(value){"dark"->"Donker";"light"->"Licht";else->"Systeem"})})} }
    Text("Taal van de navigatie")
    Row {listOf("nl" to "Nederlands","en" to "English").forEach {(value,title)->FilterChip(selected=pref.language==value,onClick={model.save(pref.copy(language=value))},label={Text(title)})}}
    Text("Spreeksnelheid: %.1f×".format(pref.speed))
    Slider(value=pref.speed,onValueChange={model.save(pref.copy(speed=it))},valueRange=.7f..1.5f)
    Row(verticalAlignment=Alignment.CenterVertically){Switch(pref.voiceOutput,{model.save(pref.copy(voiceOutput=it))});Text("Antwoorden uitspreken",Modifier.padding(start=12.dp))}
    Text("Microfoon")
    model.audio.devices(true).forEach {(id,title)->FilterChip(selected=pref.inputDevice==id,onClick={model.save(pref.copy(inputDevice=id))},label={Text(title)})}
    Text("Luidspreker")
    model.audio.devices(false).forEach {(id,title)->FilterChip(selected=pref.outputDevice==id,onClick={model.save(pref.copy(outputDevice=id))},label={Text(title)})}
    Text("Formulieren en spraak: Nederlands. Wakeword op de achtergrond is nog niet beschikbaar. Er wordt geen ruwe audio opgeslagen. Alleen je transcript en chatcontext gaan naar de gekozen AI-provider; spraakherkenning en Piper draaien op jouw server.",style=MaterialTheme.typography.bodySmall)
    Text("Diagnostiek: ${state.connection.title}\nVersie ${BuildConfig.VERSION_NAME}",style=MaterialTheme.typography.bodySmall)
    HorizontalDivider(Modifier.padding(vertical=16.dp))
    NaturalSettingsScreen(state,model)
}
