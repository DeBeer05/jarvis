package nl.jarvis.mobile

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import nl.jarvis.mobile.features.*
import org.json.JSONObject
import java.time.ZonedDateTime
import java.time.ZoneId

@Composable fun AutomationScreen(state: ScreenState, model: JarvisViewModel) {
    val context=LocalContext.current
    var section by remember { mutableStateOf("Herinneringen") }
    val sections=listOf("Agenda","Herinneringen","Goedkeuringen","Automatiseringen","Workflows","Meldingen","Accounts")
    var menu by remember { mutableStateOf(false) }
    Box { OutlinedButton(onClick={menu=true}) { Text(section) }; DropdownMenu(menu,{menu=false}) { sections.forEach { name -> DropdownMenuItem(text={Text(name)},onClick={section=name;menu=false}) } } }
    Text("Zelfstandig binnen regels",style=MaterialTheme.typography.titleLarge)
    Text("Rechten worden door de eigenaar verleend. Externe wijzigingen vragen aparte goedkeuring.")
    Button(onClick=model::automationRefresh) { Text("Vernieuwen") }
    var priority by remember {mutableIntStateOf(1)};var deadline by remember {mutableStateOf<String?>(null)}
    if(section in listOf("Herinneringen","Automatiseringen","Workflows")) {
        SelectValue("Prioriteit",priority.toString(),mapOf("0" to "Laag","1" to "Normaal","2" to "Belangrijk","3" to "Urgent")){priority=it.toInt()}
        DateField("Optionele deadline",deadline,true){deadline=it}
    }
    if(section=="Herinneringen") {
        var text by remember { mutableStateOf("") };var at by remember { mutableStateOf(ZonedDateTime.now().plusHours(1).toOffsetDateTime().toString()) };var repeat by remember { mutableStateOf("once") }
        OutlinedTextField(text,{text=it},label={Text("Waarvoor?")},modifier=Modifier.fillMaxWidth())
        DateField("Herinnering op",at,false){if(it!=null)at=it}
        Row { listOf("once","daily","weekly").forEach { value -> TextButton(onClick={repeat=value}) {Text(if(value==repeat) "✓ $value" else value)} } }
        Button(onClick={model.automationSubmit("ReminderCreate",JSONObject().put("text",text).put("at",at).put("repeat",repeat).put("timezone",ZoneId.systemDefault().id).toString(),priority,deadline)}) {Text("Herinnering instellen")}
    }
    if(section=="Agenda") {
        var start by remember {mutableStateOf(ZonedDateTime.now().toOffsetDateTime().toString())};var end by remember {mutableStateOf(ZonedDateTime.now().plusDays(7).toOffsetDateTime().toString())}
        OutlinedTextField(start,{start=it},label={Text("Vanaf, met tijdzone")});OutlinedTextField(end,{end=it},label={Text("Tot, met tijdzone")})
        Button(onClick={model.automationRequest("/calendar/search","POST",JSONObject().put("calendar_id","primary").put("start",start).put("end",end).put("query",""))}) {Text("Agenda bekijken")}
    }
    if(section=="Accounts") {
        Text("Google koppelen en rechten beheren gebeurt in de eigenaarinterface op je computer.")
        TextButton(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(state.preferences.origin+"/automations")))}) {Text("Eigenaarinterface openen")}
    }
    val jobs=try {JSONObject(state.automations).optJSONArray("items")}catch(_:Exception){null}
    var decision by remember {mutableStateOf<Pair<String,Boolean>?>(null)}
    if(jobs!=null) for(i in 0 until jobs.length()) {
        val job=jobs.getJSONObject(i);val status=job.getString("status");val id=job.getString("id")
        if(section=="Goedkeuringen" && status!="approval") continue
        Card(Modifier.fillMaxWidth()) {Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
            Text(job.getString("tool")+" · "+status,style=MaterialTheme.typography.titleMedium)
            Text(job.getJSONObject("payload").toString(2))
            Row {if(status=="approval") {TextButton(onClick={decision=id to true}){Text("Goedkeuren")};TextButton(onClick={decision=id to false}){Text("Weigeren")}}
                if(status=="queued") TextButton(onClick={model.automationControl(id,"paused")}){Text("Pauzeren")}
                if(status=="paused") TextButton(onClick={model.automationControl(id,"queued")}){Text("Hervatten")}
                if(status=="completed")TextButton(onClick={model.automationUndo(id)}){Text("Herstelvoorstel")}
                if(status in listOf("queued","paused","approval","waiting","blocked")) TextButton(onClick={model.automationControl(id,"cancelled")}){Text("Annuleren")}
            }
        }}
    }
    decision?.let { value -> AlertDialog(onDismissRequest={decision=null},title={Text("Exacte actie bevestigen")},text={Text("Controleer hierboven de ontvangers, inhoud en gevolgen. Deze toestemming geldt uitsluitend voor dit voorstel.")},confirmButton={TextButton(onClick={decision=null;model.automationDecide(value.first,value.second)}){Text("Bevestigen")}},dismissButton={TextButton(onClick={decision=null}){Text("Terug")}}) }
    if(section=="Automatiseringen" || section=="Workflows") {
        var tool by remember {mutableStateOf("WorkflowCreate")};var input by remember {mutableStateOf("{}")};var submit by remember {mutableStateOf(false)}
        OutlinedTextField(tool,{tool=it},label={Text("Geregistreerde actie")});OutlinedTextField(input,{input=it},label={Text("Actiegegevens (JSON)")},minLines=3)
        Button(onClick={submit=true}){Text("Voorstel indienen")}
        if(submit) AlertDialog(onDismissRequest={submit=false},title={Text(tool)},text={Text(input)},confirmButton={TextButton(onClick={submit=false;model.automationSubmit(tool,input,priority,deadline)}){Text("Indienen")}},dismissButton={TextButton(onClick={submit=false}){Text("Annuleren")}})
    }
    if(section=="Meldingen") {Text("Meldingsrechten en categorieën vind je ook in Meldingen. Externe pushbezorging is nog niet geconfigureerd.");Text(state.automations)}
    if(state.automationResult.isNotBlank()) Text(state.automationResult)
    TextButton(onClick={context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {type="text/plain";putExtra(Intent.EXTRA_TEXT,state.automationResult)},"Bericht zelf delen"))}) {Text("Resultaat handmatig delen")}
}
