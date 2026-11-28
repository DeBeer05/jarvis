package nl.jarvis.mobile

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import nl.jarvis.mobile.features.JarvisViewModel
import nl.jarvis.mobile.features.ScreenState
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.roundToInt

private fun objectOrEmpty(text: String): JSONObject = try { JSONObject(text) } catch(_:Exception) { JSONObject() }
private fun JSONObject.namesList(): List<String> = keys().asSequence().toList()
private fun JSONArray.strings(): List<String> = (0 until length()).map {getString(it)}

@Composable private fun NaturalDiagnostics(state:ScreenState,model:JarvisViewModel,export:()->Unit) {
    Text("Metingen bevatten geen gespreksinhoud of sleutels. RAM/CPU gelden voor de server en zijn geen meting van de toekomstige mini-pc.")
    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
        Button(onClick=model::naturalDiagnostics){Text("Vernieuwen")}
        OutlinedButton(onClick=export){Text("Exporteren")}
    }
    if(state.naturalDiagnostics.isBlank()) {Text("Nog niet gemeten");return}
    val data=objectOrEmpty(state.naturalDiagnostics);val latency=data.optJSONObject("latency") ?: JSONObject()
    val resources=data.optJSONObject("resources") ?: JSONObject()
    fun seconds(key:String)=if(latency.has(key)&&!latency.isNull(key))String.format(java.util.Locale.ROOT,"%.3f s",latency.getDouble(key)/1000) else "Nog niet gemeten"
    fun mib(key:String)=if(resources.has(key)&&!resources.isNull(key))String.format(java.util.Locale.ROOT,"%.1f MiB",resources.getDouble(key)/1048576) else "Niet gemeten"
    val rows=listOf(
        "Server en database" to "Online · database gecontroleerd",
        "Laatst gebruikte AI" to if(data.isNull("active_provider"))"Nog geen antwoord" else data.optString("active_provider","Onbekend"),
        "Microfoon" to state.voiceStatus,
        "Spraakgesprek" to state.conversationState,
        "Verbinding" to "Geauthenticeerde HTTP/SSE · WebSocket nog niet geconfigureerd",
        "STT / TTS" to if(data.optJSONObject("voice")?.optBoolean("inference_busy")==true)"Spraakengine bezig" else if(data.optJSONObject("voice")?.optJSONObject("capabilities")?.optBoolean("runtime_installed")==true)"Runtime aanwezig" else "Runtime niet geïnstalleerd",
        "Geheugen" to "${data.optJSONObject("memory_counts")?.optInt("active",0) ?: 0} actieve herinneringen",
        "Google-koppeling" to if(data.optJSONObject("integrations")?.optBoolean("google_connected")==true)"Gekoppeld" else "Niet gekoppeld",
        "CPU server (één kern = 100%)" to if(resources.has("cpu_one_core_percent")&&!resources.isNull("cpu_one_core_percent"))"${resources.getDouble("cpu_one_core_percent")}%" else "Ververs voor een tweede meting",
        "RAM server / spraakhelper" to "${mib("resident_bytes")} / ${mib("voice_helper_resident_bytes")}",
        "GPU" to if(resources.has("gpu_percent")&&!resources.isNull("gpu_percent"))"${resources.getDouble("gpu_percent")}% (hele machine)" else "Niet gemeten",
        "STT (server)" to seconds("stt_ms"),
        "Eerste AI-tekst (server)" to seconds("ai_first_token_ms"),
        "TTS-aanvraag (server)" to seconds("tts_ms"),
        "Begin audio-uitvoer (client)" to seconds("native_first_audio_ms"),
        "Totale antwoordtijd (server)" to seconds("response_total_ms"),
        "Contextgrootte (geschatte tokens)" to if(latency.isNull("context_tokens"))"Nog niet gemeten" else latency.optDouble("context_tokens",0.0).roundToInt().toString())
    Column(Modifier.heightIn(max=520.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)) {
        rows.forEach {(title,value)->Card(Modifier.fillMaxWidth()) {Column(Modifier.padding(12.dp)) {Text(title,style=MaterialTheme.typography.labelLarge);Text(value)}}}
        val events=data.optJSONArray("events") ?: JSONArray()
        val counts=listOf("interruption","rejected_interruption","wake_miss").associateWith {event->(0 until events.length()).map{events.getJSONObject(it)}.filter{it.optString("event")==event}.sumOf{it.optDouble("metric",0.0)}}
        Text("Onderbrekingen: ${counts["interruption"]?.roundToInt() ?: 0} · afgewezen spraak/wakekandidaten: ${((counts["rejected_interruption"] ?: 0.0)+(counts["wake_miss"] ?: 0.0)).roundToInt()} (bewaarde meetperiode)")
        Text("Laatste foutcodes: "+(0 until events.length()).map{events.getJSONObject(it)}.filter{!it.isNull("code")}.map{it.getString("code")}.distinct().joinToString().ifBlank{"Geen bewaarde foutcodes"})
    }
}

internal object SettingsDraft {
    fun canonical(value: Any?): String = when(value) {
        null,JSONObject.NULL -> "null"
        is JSONObject -> value.namesList().sorted().joinToString(",","{","}") {JSONObject.quote(it)+":"+canonical(value.opt(it))}
        is JSONArray -> (0 until value.length()).joinToString(",","[","]") {canonical(value.opt(it))}
        is Number -> value.toDouble().toString()
        is Boolean -> value.toString()
        else -> JSONObject.quote(value.toString())
    }
    fun validated(text: String,schema: JSONObject): JSONObject {
        val result=JSONObject(text);val definitions=schema.getJSONObject("user").getJSONObject("\$defs")
        val properties=schema.getJSONObject("user").getJSONObject("properties")
        result.namesList().forEach { category ->
            val name=properties.getJSONObject(category).getString("\$ref").substringAfterLast('/')
            val fields=definitions.getJSONObject(name).getJSONObject("properties");val values=result.getJSONObject(category)
            fields.namesList().forEach { key ->
                val field=fields.getJSONObject(key);val value=values.opt(key)
                if(field.optString("type") in setOf("integer","number")) {
                    val numeric=value?.toString()?.toDoubleOrNull() ?: error("Controleer ${field.optString("title",key)}")
                    require(numeric.isFinite() && numeric>=field.optDouble("minimum",-Double.MAX_VALUE) && numeric<=field.optDouble("maximum",Double.MAX_VALUE)) {"Waarde buiten bereik: $key"}
                    if(field.optString("type")=="integer") { require(numeric%1.0==0.0);values.put(key,numeric.toInt()) } else values.put(key,numeric)
                }
            }
        }
        return result
    }
}

@Composable fun NaturalSettingsScreen(state: ScreenState,model: JarvisViewModel) {
    Text("Gesprekken en geheugen",style=MaterialTheme.typography.headlineSmall)
    Text(state.naturalStatus.ifBlank {"Globale voorkeuren synchroniseren met Windows. Microfoon en luidspreker blijven lokaal."})
    if(!state.connection.authenticated) { Text("Log in en koppel deze telefoon om je persoonlijke instellingen te openen.");return }
    var page by remember {mutableStateOf("Instellingen")}
    Row(Modifier.horizontalScroll(rememberScrollState())) {listOf("Instellingen","Butler","Beeldcontext","Geheugen","Adresboek","Voice Studio","Diagnostiek","Aanwezigheid").forEach {name ->FilterChip(selected=page==name,onClick={page=name;if(name=="Geheugen")model.naturalMemory();if(name=="Adresboek")model.naturalContacts();if(name=="Voice Studio")model.voiceStudio();if(name=="Diagnostiek")model.naturalDiagnostics();if(name=="Aanwezigheid")model.presenceRefresh()},label={Text(name)})}}
    val context=LocalContext.current;val scope=rememberCoroutineScope();var exportText by remember {mutableStateOf("")}
    val export=rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) {uri -> if(uri!=null) scope.launch {
        try { withContext(Dispatchers.IO) { context.contentResolver.openOutputStream(uri)?.use {it.write(exportText.toByteArray(Charsets.UTF_8))} ?: error("Geen uitvoerbestand") };model.message("Export opgeslagen") }
        catch(_:Exception) {model.message("Export kon niet worden opgeslagen")};exportText=""
    } }
    fun exportData(path: String,name: String) {model.exportNatural(path) {text -> exportText=text;export.launch(name)}}
    if(page=="Butler") {ButlerScreen(state,model);return}
    if(page=="Beeldcontext") {ImageContextScreen(state,model);return}
    if(page=="Voice Studio") {VoiceStudio(state,model);return}
    if(page=="Adresboek") {NaturalContacts(state,model);return}
    if(page=="Geheugen") {NaturalMemory(state,model) {exportData("/memory/export","jarvis-geheugen.json")};return}
    if(page=="Diagnostiek") {NaturalDiagnostics(state,model) {exportData("/diagnostics","jarvis-diagnostiek.json")};return}
    if(page=="Aanwezigheid") {
        Text(state.presenceStatus.ifBlank {"Aanwezigheid delen staat standaard uit"})
        Text("Alleen vergrendeling en inactiviteit terwijl JARVIS vooraan staat. Geen schermbeelden, locatie of gebruik van andere apps. Achtergrondstatus vereist later een afzonderlijk ingeschakelde service. Globale modi staan onder Instellingen → Aanwezigheid en modi.")
        val document=objectOrEmpty(state.presenceDevice)
        val enabled=document.optJSONObject("settings")?.optBoolean("presence_allowed")==true
        Row(verticalAlignment=Alignment.CenterVertically) {
            Switch(checked=enabled,onCheckedChange=model::presenceSave,enabled=state.presenceDevice.isNotBlank())
            Text("Aanwezigheidsstatus van deze telefoon delen")
        }
        OutlinedButton(onClick=model::presenceRefresh){Text("Vernieuwen")}
        return
    }
    if(state.naturalSchema.isBlank() || state.naturalSettings.isBlank()) {Button(onClick=model::naturalRefresh){Text("Instellingen ophalen")};return}
    val schema=remember(state.naturalSchema) {JSONObject(state.naturalSchema)}
    var base by remember {mutableStateOf(state.naturalSettings)}
    var draft by remember {mutableStateOf(JSONObject(state.naturalSettings).getJSONObject("settings").toString())}
    var dirty by remember {mutableStateOf(false)};var submitted by remember {mutableStateOf<String?>(null)}
    var conflict by remember {mutableStateOf(false)};var category by remember {mutableStateOf("general")};var search by remember {mutableStateOf("")}
    var reset by remember {mutableStateOf(false)};var importText by remember {mutableStateOf<String?>(null)}
    LaunchedEffect(state.naturalSettings) {
        val remote=JSONObject(state.naturalSettings);val matches=submitted==SettingsDraft.canonical(remote.getJSONObject("settings"))
        if(!dirty || matches) {base=state.naturalSettings;draft=remote.getJSONObject("settings").toString();dirty=false;submitted=null;conflict=false}
        else conflict=remote.getInt("revision")!=JSONObject(base).getInt("revision")
    }
    val import=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {uri -> if(uri!=null) scope.launch {
        try {importText=withContext(Dispatchers.IO) {context.contentResolver.openInputStream(uri)?.use {stream ->
            val bytes=ByteArray(100001);var count=0
            while(count<bytes.size) {val read=stream.read(bytes,count,bytes.size-count);if(read<0)break;count+=read}
            require(count<=100000);String(bytes,0,count,Charsets.UTF_8)
        } ?: error("Geen bestand")}} catch(_:Exception) {model.message("Ongeldig of te groot instellingenbestand")}
    } }
    if(conflict) Text("Elders gewijzigd. Je invoer blijft staan; kies Annuleren om de nieuwste versie te laden.",color=MaterialTheme.colorScheme.error)
    if(dirty) Text("Niet-opgeslagen wijzigingen",color=MaterialTheme.colorScheme.primary)
    OutlinedTextField(search,{search=it},label={Text("Instellingen zoeken")},modifier=Modifier.fillMaxWidth())
    val labels=schema.optJSONObject("labels") ?: JSONObject();val values=schema.optJSONObject("values") ?: JSONObject()
    val categories=schema.getJSONObject("categories");val definitions=schema.getJSONObject("user").getJSONObject("\$defs")
    val properties=schema.getJSONObject("user").getJSONObject("properties")
    val visible=categories.namesList().filter {name ->
        val definition=definitions.getJSONObject(properties.getJSONObject(name).getString("\$ref").substringAfterLast('/')).getJSONObject("properties")
        (categories.getString(name)+" "+definition.namesList().joinToString(" "){labels.optString(it,it)}).contains(search,true)
    }
    if(category !in visible && visible.isNotEmpty()) LaunchedEffect(visible) {category=visible.first()}
    Choice("Categorie",category,visible.map {it to categories.getString(it)}) {category=it}
    val definition=definitions.getJSONObject(properties.getJSONObject(category).getString("\$ref").substringAfterLast('/')).getJSONObject("properties")
    val settings=JSONObject(draft).getJSONObject(category)
    key(category) {definition.namesList().forEach {name ->
        val field=definition.getJSONObject(name)
        if(category=="voice" && !voiceFieldVisible(field,settings))return@forEach
        NaturalField(name,labels.optString(name,field.optString("title",name)),field,settings.opt(name),schema,values) {value ->
            val changed=JSONObject(draft);changed.getJSONObject(category).put(name,value);draft=changed.toString();dirty=true
        }
    }}
    var preview by remember(state.connection.authenticated) {mutableStateOf<String?>(null)}
    if(category=="personality") {
        OutlinedButton(onClick={try {
            val ready=SettingsDraft.validated(draft,schema)
            preview="Voorbeeld genereren…"
            model.previewNaturalPersonality(ready.getJSONObject("personality").toString()) {preview=it}
        } catch(_:Exception){model.message("Controleer de persoonlijkheidsinstellingen")}}) {Text("Voorbeeldgesprek testen")}
    }
    preview?.let {text->AlertDialog(onDismissRequest={preview=null},title={Text("Persoonlijkheidsvoorbeeld")},
        text={Text(text+"\n\nNiet opgeslagen. Er worden geen taken uitgevoerd.")},
        confirmButton={TextButton(onClick={preview=null}){Text("Sluiten")}})}
    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
        Button(onClick={try {val ready=SettingsDraft.validated(draft,schema);submitted=SettingsDraft.canonical(ready);model.saveNaturalSettings(ready.toString(),JSONObject(base).getInt("revision"))} catch(_:Exception){model.message("Controleer de numerieke instellingen en hun toegestane bereik")}},enabled=dirty&&!conflict,modifier=Modifier.testTag("natural-save")){Text("Opslaan")}
        OutlinedButton(onClick={base=state.naturalSettings;draft=JSONObject(base).getJSONObject("settings").toString();dirty=false;conflict=false;submitted=null}){Text("Annuleren")}
    }
    Row {TextButton(onClick={reset=true},enabled=!dirty&&!conflict){Text("Standaardwaarden")};TextButton(onClick=model::naturalRefresh){Text("Vernieuwen")}}
    Row {TextButton(onClick={exportData("/settings/export","jarvis-instellingen.json")}){Text("Exporteren")};TextButton(onClick={import.launch(arrayOf("application/json","text/plain"))},enabled=!dirty&&!conflict){Text("Importeren")}}
    Text("Globale voorkeuren verlenen geen apparaatrechten en schakelen verplichte goedkeuringen nooit uit.",style=MaterialTheme.typography.bodySmall)
    OutlinedButton(onClick={model.navigate("Spraak")}){Text("Microfoon, stem en luidspreker testen")}
    if(reset) AlertDialog(onDismissRequest={reset=false},title={Text("Categorie herstellen?")},text={Text("De opgeslagen standaardwaarden vervangen deze categorie. Annuleer eerst als je andere invoer wilt behouden.")},confirmButton={TextButton(onClick={reset=false;dirty=false;model.resetNaturalCategory(category,JSONObject(base).getInt("revision"))}){Text("Herstellen")}},dismissButton={TextButton(onClick={reset=false}){Text("Terug")}})
    importText?.let {text ->AlertDialog(onDismissRequest={importText=null},title={Text("Instellingen importeren?")},text={Text("Vervang de globale voorkeuren door dit bestand. Geheimen zijn niet toegestaan.")},confirmButton={TextButton(onClick={importText=null;dirty=false;model.importNatural(text,JSONObject(base).getInt("revision"))}){Text("Importeren")}},dismissButton={TextButton(onClick={importText=null}){Text("Terug")}})}
}

@Composable private fun Choice(title: String,value: String,choices: List<Pair<String,String>>,disabled: Set<String> = emptySet(),change:(String)->Unit) {
    var open by remember {mutableStateOf(false)}
    Column {Text(title,style=MaterialTheme.typography.labelLarge);Box {
        OutlinedButton(onClick={open=true},enabled=choices.isNotEmpty()) {Text(choices.firstOrNull{it.first==value}?.second ?: value.ifBlank {"Kies…"})}
        DropdownMenu(open,{open=false}) {choices.forEach {(id,label)->DropdownMenuItem(text={Text(label+if(id in disabled)" · niet geïnstalleerd" else "")},enabled=id !in disabled,onClick={open=false;change(id)})}}
    }}
}

@Composable private fun NaturalField(name: String,title: String,field: JSONObject,value: Any?,schema: JSONObject,labels: JSONObject,change:(Any)->Unit) {
    val modifier=Modifier.fillMaxWidth().testTag("natural-$name")
    when {
        field.has("const") -> Text("$title: ${if(value==false)"uitgeschakeld" else value}",modifier)
        field.has("enum") -> Choice(title,value.toString(),field.getJSONArray("enum").strings().map {it to labels.optString(it,it)},disabled=field.optJSONArray("x-unavailable")?.strings()?.toSet() ?: emptySet(),change=change)
        field.optString("type")=="boolean" -> Row(verticalAlignment=Alignment.CenterVertically) {Switch(value==true,{change(it)},modifier=Modifier.testTag("natural-$name"));Text(title,Modifier.padding(start=10.dp))}
        field.optString("type")=="object" && field.optJSONObject("additionalProperties")?.optString("type")=="string" && field.optJSONObject("additionalProperties")?.optJSONArray("enum")==null -> {
            fun parsed(text:String):JSONObject {
                val result=JSONObject()
                text.lines().filter {it.isNotBlank()}.forEach {line->
                    val pair=line.split(":",limit=2)
                    require(pair.size==2 && pair[0].isNotBlank() && pair[1].isNotBlank())
                    result.put(pair[0].trim(),pair[1].trim())
                }
                return result
            }
            val current=value as? JSONObject ?: JSONObject()
            var text by remember(current.toString()) {mutableStateOf(current.keys().asSequence().joinToString("\n"){it+": "+current.optString(it)})}
            val valid=runCatching {parsed(text)}.isSuccess
            OutlinedTextField(text,{text=it;runCatching {parsed(it)}.getOrNull()?.let(change)},label={Text(title)},placeholder={Text("Sam: houdt van wandelen")},isError=!valid,modifier=modifier)
        }
        field.optString("type")=="object" -> {
            Text(title,style=MaterialTheme.typography.titleMedium)
            val current=value as? JSONObject ?: JSONObject();val mandatory=schema.optJSONArray("mandatory_approval")?.strings() ?: emptyList()
            schema.optJSONArray("actions")?.strings()?.forEach {tool ->
                Choice(schema.optJSONObject("labels")?.optString(tool,tool) ?: tool,current.optString(tool,"inherit"),listOf("inherit" to "Volgens profiel en vaste veiligheidsregels")+listOf("ask","advise","allow","block").filter {it!="allow"||tool !in mandatory}.map {it to labels.optString(it,it)}) {selected -> val result=JSONObject(current.toString());if(selected=="inherit")result.remove(tool) else result.put(tool,selected);change(result)}
            }
        }
        field.optString("type")=="array" && field.getJSONObject("items").optString("type")=="integer" -> {
            Text(title);val selected=(value as? JSONArray)?.let {array->(0 until array.length()).map {array.getInt(it)}} ?: emptyList()
            Column {listOf(listOf(0,1,2,3),listOf(4,5,6)).forEach {group->Row {group.forEach {day->FilterChip(selected=day in selected,onClick={change(JSONArray(if(day in selected)selected-day else (selected+day).sorted()))},label={Text(listOf("Ma","Di","Wo","Do","Vr","Za","Zo")[day])})}}}}
        }
        field.optString("type")=="array" -> OutlinedTextField((value as? JSONArray)?.strings()?.joinToString("\n") ?: "",{change(JSONArray(it.lines().map(String::trim).filter(String::isNotEmpty)))},label={Text(title)},modifier=modifier,minLines=2)
        field.optString("type") in setOf("integer","number") -> {
            val text=value?.toString() ?: "";val numeric=text.toDoubleOrNull();val valid=numeric!=null&&numeric.isFinite()&&numeric>=field.optDouble("minimum",0.0)&&numeric<=field.optDouble("maximum",Double.MAX_VALUE)
            if(field.optDouble("minimum",-1.0)==0.0 && field.optDouble("maximum",-1.0)==100.0) {
                Text("$title: ${numeric?.toInt() ?: 0}");Slider((numeric?.toFloat() ?: 0f).coerceIn(0f,100f),{change(it.roundToInt())},valueRange=0f..100f,modifier=modifier)
            } else OutlinedTextField(text,{change(it)},label={Text(title)},isError=!valid,supportingText={Text("${field.optDouble("minimum",0.0)} – ${field.optDouble("maximum",100000.0)}")},singleLine=true,modifier=modifier)
        }
        else -> OutlinedTextField(value?.toString() ?: "",{change(it)},label={Text(title)},modifier=modifier,minLines=if(field.optInt("maxLength")>300)3 else 1)
    }
}

@Composable private fun NaturalMemory(state: ScreenState,model: JarvisViewModel,export:()->Unit) {
    var query by remember {mutableStateOf("")};var category by remember {mutableStateOf("")}
    var editing by remember {mutableStateOf<JSONObject?>(null)};var deleting by remember {mutableStateOf<String?>(null)};var clear by remember {mutableStateOf(false)}
    Text("Herinneringen",style=MaterialTheme.typography.titleLarge)
    Text("Vergeten verwijdert het geheugen en afgeleide context. Oorspronkelijke gesprekken staan afzonderlijk in Gesprekken.")
    OutlinedTextField(query,{query=it},label={Text("Geheugen zoeken")},modifier=Modifier.fillMaxWidth())
    val categories=listOf("preference","person","project","work","activity","hobby","habit","decision","technical","location","instruction","conversation")
    Choice("Categorie",category,listOf("" to "Alle categorieën")+categories.map {it to it}) {category=it}
    Row {Button(onClick={model.naturalMemory(query,category)}){Text("Zoeken")};TextButton(onClick={editing=JSONObject()}){Text("Toevoegen")};TextButton(onClick=export){Text("Exporteren")}}
    val data=objectOrEmpty(state.naturalMemory);val items=data.optJSONArray("items") ?: JSONArray()
    for(index in 0 until items.length()) {val item=items.getJSONObject(index)
        Card(Modifier.fillMaxWidth()) {Column(Modifier.padding(12.dp)) {
            Text(item.optString("category")+" · "+item.optString("status"),style=MaterialTheme.typography.labelLarge)
            Text(item.getString("content"))
            Row {TextButton(onClick={editing=item}){Text("Wijzigen")};TextButton(onClick={deleting=item.getString("id")}){Text("Verwijderen")}}
        }}
    }
    if(data.optBoolean("has_more"))Text("Meer resultaten beschikbaar. Verfijn je zoekopdracht.")
    TextButton(onClick={clear=true}){Text("Alle herinneringen en samenvattingen wissen")}
    editing?.let {item -> key(item.optString("id","new")) {
        var content by remember {mutableStateOf(item.optString("content"))};var selected by remember {mutableStateOf(item.optString("category","preference"))};var consent by remember {mutableStateOf(false)};var outdated by remember {mutableStateOf(item.optString("status")=="outdated")}
        AlertDialog(onDismissRequest={editing=null},title={Text(if(item.has("id"))"Herinnering wijzigen" else "Herinnering toevoegen")},text={Column(Modifier.verticalScroll(rememberScrollState())) {
            OutlinedTextField(content,{content=it},label={Text("Inhoud")},minLines=3);Choice("Categorie",selected,categories.map{it to it}){selected=it}
            Row(verticalAlignment=Alignment.CenterVertically){Checkbox(consent,{consent=it});Text("Ik geef expliciet toestemming voor deze gevoelige herinnering")}
            Row(verticalAlignment=Alignment.CenterVertically){Checkbox(outdated,{outdated=it});Text("Verouderd")}
        }},confirmButton={TextButton(onClick={
            val input=JSONObject().put("content",content).put("category",selected).put("consent_sensitive",consent).put("sensitivity",if(consent)"sensitive" else item.optString("sensitivity","normal")).put("status",if(outdated)"outdated" else "active")
            if(item.has("id")) {input.put("revision",item.getInt("revision")).put("key",item.getString("memory_key")).put("kind",item.getString("kind")).put("confidence",item.getDouble("confidence"));if(!item.isNull("expires"))input.put("expires_at",item.getDouble("expires"))}
            model.naturalMemorySave(input,item.optString("id").ifBlank{null});editing=null
        },enabled=content.isNotBlank()){Text("Opslaan")}},dismissButton={TextButton(onClick={editing=null}){Text("Annuleren")}})
    }}
    deleting?.let {id->AlertDialog(onDismissRequest={deleting=null},title={Text("Herinnering verwijderen?")},text={Text("Dit verwijdert de herinnering en afgeleide context. Het oorspronkelijke gesprek blijft bestaan.")},confirmButton={TextButton(onClick={deleting=null;model.naturalMemoryDelete(id)}){Text("Verwijderen")}},dismissButton={TextButton(onClick={deleting=null}){Text("Terug")}})}
    if(clear)AlertDialog(onDismissRequest={clear=false},title={Text("Volledig geheugen wissen?")},text={Text("Alle persoonlijke herinneringen en samenvattingen worden verwijderd. Gesprekken worden afzonderlijk beheerd.")},confirmButton={TextButton(onClick={clear=false;model.naturalMemoryClear()}){Text("Wissen")}},dismissButton={TextButton(onClick={clear=false}){Text("Terug")}})
    Text("Gesprekssamenvattingen",style=MaterialTheme.typography.titleLarge)
    val summaries=objectOrEmpty(state.naturalSummaries).optJSONArray("items") ?: JSONArray()
    for(index in 0 until summaries.length()) {val summary=summaries.getJSONObject(index)
        key(summary.getString("id"),summary.getInt("revision")) {var text by remember {mutableStateOf(summary.getString("content"))}
            Text("Gesprek "+summary.getString("conversation_id").take(8));OutlinedTextField(text,{text=it},label={Text("Samenvatting")},modifier=Modifier.fillMaxWidth(),minLines=2)
            TextButton(onClick={model.naturalSummarySave(summary.getString("id"),text,summary.getInt("revision"))}){Text("Samenvatting opslaan")}
        }
    }
}


@Composable private fun NaturalContacts(state:ScreenState,model:JarvisViewModel) {
    var query by remember {mutableStateOf("")};var editing by remember {mutableStateOf<JSONObject?>(null)}
    var deleting by remember {mutableStateOf<JSONObject?>(null)}
    Text("Noem een opgeslagen naam bij het maken van een mail. Controleer het volledige adres in het verzendvoorstel. Maximaal 200 contacten, 8 aliassen per contact.")
    OutlinedTextField(query,{query=it},label={Text("Zoek naam, alias of e-mailadres")},modifier=Modifier.fillMaxWidth())
    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
        Button(onClick={editing=JSONObject()}){Text("Toevoegen")}
        OutlinedButton(onClick=model::naturalContacts){Text("Vernieuwen")}
    }
    val items=objectOrEmpty(state.naturalContacts).optJSONArray("items") ?: JSONArray()
    Column(Modifier.heightIn(max=500.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)) {
        if(items.length()==0)Text("Nog geen contacten opgehaald of opgeslagen.")
        (0 until items.length()).map{items.getJSONObject(it)}.filter{item->listOf(item.optString("name"),item.optString("email"),item.optJSONArray("aliases").toString()).any{it.contains(query,true)}}.forEach {item ->
            Card(Modifier.fillMaxWidth()) {Column(Modifier.padding(12.dp)) {
                Text(item.getString("name"),style=MaterialTheme.typography.titleMedium);Text(item.getString("email"))
                Text((item.optJSONArray("aliases") ?: JSONArray()).strings().joinToString(", "))
                Row {TextButton(onClick={editing=item}){Text("Wijzigen")};TextButton(onClick={deleting=item}){Text("Verwijderen")}}
            }}
        }
    }
    editing?.let {item ->
        var name by remember(item) {mutableStateOf(item.optString("name"))};var email by remember(item) {mutableStateOf(item.optString("email"))}
        var aliases by remember(item) {mutableStateOf((item.optJSONArray("aliases") ?: JSONArray()).strings().joinToString("\n"))}
        AlertDialog(onDismissRequest={editing=null},title={Text(if(item.has("id"))"Contact wijzigen" else "Contact toevoegen")},text={
            Column(Modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(name,{name=it},label={Text("Naam")},singleLine=true)
                OutlinedTextField(email,{email=it},label={Text("E-mailadres")},singleLine=true)
                OutlinedTextField(aliases,{aliases=it},label={Text("Aliassen, één per regel")})
                Text(state.naturalStatus)
            }
        },confirmButton={TextButton(onClick={
            val data=JSONObject().put("name",name.trim()).put("email",email.trim()).put("aliases",JSONArray(aliases.lines().map{it.trim()}.filter{it.isNotBlank()}))
            if(item.has("id"))data.put("revision",item.getInt("revision"))
            model.naturalContactSave(data,if(item.has("id"))item.getString("id") else null){editing=null}
        }){Text("Opslaan")}},dismissButton={TextButton(onClick={editing=null}){Text("Annuleren")}})
    }
    deleting?.let {item ->AlertDialog(onDismissRequest={deleting=null},title={Text("Contact verwijderen?")},text={Text("Bestaande mailvoorstellen blijven ongewijzigd.")},confirmButton={TextButton(onClick={model.naturalContactDelete(item.getString("id"),item.getInt("revision"));deleting=null}){Text("Verwijderen")}},dismissButton={TextButton(onClick={deleting=null}){Text("Annuleren")}})}
}


@Composable private fun VoiceStudio(state:ScreenState,model:JarvisViewModel) {
    var text by remember {mutableStateOf("Goedemorgen, meneer. Uw agenda is bijgewerkt en u heeft twee belangrijke berichten ontvangen.")}
    var speed by remember {mutableFloatStateOf(.95f)};var volume by remember {mutableFloatStateOf(.8f)};var selected by remember {mutableIntStateOf(0)}
    val voices=mutableListOf<Pair<String,String>>()
    val providers=objectOrEmpty(state.voiceStudio).optJSONArray("providers") ?: JSONArray()
    (0 until providers.length()).map{providers.getJSONObject(it)}.forEach {provider ->
        val list=provider.optJSONArray("voices") ?: JSONArray()
        (0 until list.length()).map{list.getJSONObject(it)}.filter{it.optBoolean("available")}.forEach {voices.add(provider.getString("id") to it.getString("id"))}
    }
    fun settings(choice:Pair<String,String>):JSONObject {
        val voice=JSONObject(JSONObject(state.naturalSettings).getJSONObject("settings").getJSONObject("voice").toString())
        voice.put("profile","custom").put("mode","manual").put("tts_provider",choice.first).put("speed",speed.toDouble()).put("volume",volume.toDouble())
        voice.put(if(choice.first=="elevenlabs")"elevenlabs_voice_id" else if(choice.first=="supertonic")"supertonic_voice" else "voice",choice.second)
        return voice
    }
    Column(Modifier.heightIn(max=650.dp).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text("ElevenLabs verstuurt de uitgesproken tekst naar de provider en kan credits kosten, ook bij onderbreken. Vergelijken achter elkaar gebruikt alleen lokale stemmen. De microfoon blijft uit.")
        val usage=objectOrEmpty(state.voiceStudio).optJSONObject("usage");val account=objectOrEmpty(state.voiceStudio).optJSONObject("account")
        Text("Gereserveerd deze maand: ${usage?.optInt("monthly_reserved_credits",0) ?: 0} credits (schatting). Accounttegoed: ${account?.optString("remaining_credits","onbekend") ?: "onbekend"}.")
        Button(onClick=model::voiceStudio){Text("Stemmen ophalen")}
        voices.forEachIndexed {index,choice->FilterChip(selected=selected==index,onClick={selected=index},label={Text(choice.first+" · "+choice.second)})}
        OutlinedTextField(text,{text=it},label={Text("Voorbeeldtekst, maximaal 350 tekens")},modifier=Modifier.fillMaxWidth())
        Text("Spreeksnelheid ${String.format(java.util.Locale.ROOT,"%.2f",speed)}×");Slider(speed,{speed=it},valueRange=.7f..1.5f)
        Text("Volume ${(volume*100).roundToInt()}%");Slider(volume,{volume=it},valueRange=0f..1f)
        val ready=voices.isNotEmpty() && selected in voices.indices && text.length in 1..350 && state.naturalSettings.isNotBlank() && !state.busy && !state.recording
        Button(enabled=ready,onClick={model.voiceStudioCompare(text,listOf(settings(voices[selected])))}){Text("Beluisteren")}
        OutlinedButton(enabled=ready,onClick={model.voiceStudioCompare(text,voices.filter{it.first!="elevenlabs"}.map{settings(it)})}){Text("Vergelijk lokale stemmen")}
        OutlinedButton(enabled=ready,onClick={model.voiceStudioSave(settings(voices[selected]))}){Text("Als favoriete stem opslaan")}
        OutlinedButton(onClick=model::stop){Text("Stop stemvoorbeeld")}
        Text(state.naturalStatus)
    }
}
