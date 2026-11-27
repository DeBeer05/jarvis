package nl.jarvis.mobile

import android.Manifest
import android.app.DatePickerDialog
import android.app.TimePickerDialog
import android.content.Intent
import android.graphics.BitmapFactory
import android.os.Build
import android.provider.Settings
import android.util.Base64
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import nl.jarvis.mobile.features.JarvisViewModel
import nl.jarvis.mobile.features.ScreenState
import org.json.JSONArray
import org.json.JSONObject
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.UUID

private const val N="/api/v1/natural/"
private const val A="/api/v1/automation/"
private val kinds=linkedMapOf("shopping" to "Boodschappen","subscription" to "Abonnementen","occasion" to "Verjaardagen en jubilea","routine" to "Routines","application" to "Sollicitaties")
private val labels=mapOf("name" to "Naam","amount" to "Aantal of bedrag","checked" to "Afgevinkt","currency" to "Valuta","cycle" to "Periode","month" to "Maand","day" to "Dag","time" to "Tijd (uu:mm)","category" to "Soort","repeat" to "Herhaling","company" to "Werkgever","status" to "Voortgang")
private val values=mapOf("monthly" to "Maandelijks","yearly" to "Jaarlijks","weekly" to "Wekelijks","daily" to "Dagelijks","once" to "Eenmalig","birthday" to "Verjaardag","anniversary" to "Jubileum","prepared" to "Voorbereid","sent" to "Verzonden","reply_review" to "Reactie controleren","interview" to "Gesprek","rejected" to "Afgewezen","offered" to "Aanbod","closed" to "Afgesloten")
private fun JSONObject.objectList(key:String):List<JSONObject> = optJSONArray(key)?.let {array->(0 until array.length()).map {array.getJSONObject(it)}} ?: emptyList()

@Composable internal fun SelectValue(title:String,value:String,choices:Map<String,String>,change:(String)->Unit) {
    var open by remember {mutableStateOf(false)}
    Box {OutlinedButton(onClick={open=true}) {Text(title+": "+(choices[value] ?: value))}
        DropdownMenu(open,{open=false}) {choices.forEach {(key,label)->DropdownMenuItem(text={Text(label)},onClick={change(key);open=false})}}}
}

@Composable internal fun DateField(title:String,value:String?,optional:Boolean,change:(String?)->Unit) {
    val context=LocalContext.current
    val date=runCatching {ZonedDateTime.parse(value).withZoneSameInstant(java.time.ZoneId.of("Europe/Amsterdam"))}.getOrElse {ZonedDateTime.now(java.time.ZoneId.of("Europe/Amsterdam")).plusDays(1).withSecond(0).withNano(0)}
    if(optional)Row {Checkbox(value!=null,{change(if(it)date.toOffsetDateTime().toString() else null)});Text(title)}
    OutlinedButton(enabled=!optional || value!=null,onClick={
        DatePickerDialog(context,{_,year,month,day->
            TimePickerDialog(context,{_,hour,minute->change(date.withYear(year).withMonth(1).withDayOfMonth(1).withMonth(month+1).withDayOfMonth(day).withHour(hour).withMinute(minute).withSecond(0).withNano(0).toOffsetDateTime().toString())},date.hour,date.minute,true).show()
        },date.year,date.monthValue-1,date.dayOfMonth).show()
    }) {Text((if(optional)"Moment" else title)+": "+date.format(DateTimeFormatter.ofPattern("dd-MM-yyyy HH:mm")))}
}

/** No implicit requests for a privacy grant, account connection or device action. */
@Composable fun ButlerScreen(state:ScreenState,model:JarvisViewModel) {
    var page by remember {mutableStateOf("Briefings")}
    Row(Modifier.horizontalScroll(rememberScrollState())) {listOf("Briefings","Lijsten","Apparaat","Integraties").forEach {name->FilterChip(page==name,{page=name},label={Text(name)})}}
    when(page) {
        "Briefings"->BriefingControls(state,model)
        "Lijsten"->PersonalLists(model)
        "Apparaat"->DeviceControls(state,model)
        else->IntegrationControls(model)
    }
}

@Composable private fun BriefingControls(state:ScreenState,model:JarvisViewModel) {
    val scope=rememberCoroutineScope();var report by remember {mutableStateOf("")};var busy by remember {mutableStateOf(false)}
    fun request(path:String,method:String="GET",body:JSONObject?=null,format:(JSONObject)->String) {
        if(busy)return;busy=true
        scope.launch {try {report=format(model.butlerRequest(path,method,body))}catch(cancel:CancellationException){throw cancel}catch(_:Exception){report="Niet bevestigd. Controleer uw verbinding en rechten, meneer."}finally{busy=false}}
    }
    Text("Uw briefing verschijnt in JARVIS. Telefonische briefings wachten op een ondersteund oproepkanaal.")
    listOf("morning" to "Ochtendbriefing","evening" to "Avondbriefing","return" to "Terugkomstbriefing").forEach {(key,title)->
        OutlinedButton(enabled=!busy,onClick={request(N+"briefings/"+key){it.getString("text")}}){Text(title)}
    }
    OutlinedButton(enabled=!busy,onClick={request(N+"briefings/schedule","POST",JSONObject()){"Briefings ingepland: ${it.getJSONArray("scheduled").length()}. Geen oproep gestart."}}){Text("Briefings inplannen")}
    OutlinedButton(enabled=!busy,onClick={request(N+"events?history=true"){data->data.objectList("items").joinToString("\n\n"){it.getJSONObject("payload").optString("text")}.ifBlank{"Er staan geen recente meldingen klaar, meneer."}}}){Text("Meldingen en briefinggeschiedenis")}
    Button(enabled=!busy,onClick={model.stop();request(A+"safety","POST",JSONObject().put("active",true)){"Noodstop actief. Taken blijven gepauzeerd."}}){Text("Noodstop")}
    OutlinedButton(enabled=!busy,onClick={request(A+"health"){"Noodstop: ${if(it.getBoolean("stopped"))"actief" else "uit"}. Te late taken: ${it.getInt("overdue")}. Onzekere uitkomsten: ${it.getJSONObject("counts").optInt("uncertain")}."}}){Text("Veiligheidsstatus")}
    if("admin:account" in state.connection.permissions)OutlinedButton(enabled=!busy,onClick={request(A+"safety","POST",JSONObject().put("active",false)){"Stop opgeheven. Hervat taken afzonderlijk."}}){Text("Noodstop opheffen als eigenaar")}
    else Text("Een noodstop opheffen doet u in het bestaande eigenaarbeheer. Taken hervatten daarna niet automatisch.")
    Text(report)
}

@Composable private fun PersonalLists(model:JarvisViewModel) {
    val scope=rememberCoroutineScope();var kind by remember {mutableStateOf("shopping")};var schema by remember {mutableStateOf(JSONObject())}
    var items by remember {mutableStateOf(emptyList<JSONObject>())};var selected by remember {mutableStateOf<JSONObject?>(null)}
    var draft by remember {mutableStateOf(JSONObject())};var status by remember {mutableStateOf("")};var busy by remember {mutableStateOf(false)}
    var deletion by remember {mutableStateOf(false)};var mail by remember {mutableStateOf("")};var key by remember {mutableStateOf("" to "")}
    suspend fun refresh() {items=model.butlerRequest(N+"life-items?kind="+kind).objectList("items");selected=null;draft=JSONObject();key="" to ""}
    fun perform(block:suspend()->Unit) {
        if(busy)return;busy=true
        scope.launch {try {block()}catch(cancel:CancellationException){throw cancel}catch(_:Exception){status="Niet opgeslagen of ingepland. Controleer uw invoer en ververs bij een wijzigingsconflict."}finally{busy=false}}
    }
    LaunchedEffect(kind) {busy=true;try {schema=model.butlerRequest(N+"life-items/schema").getJSONObject("kinds");refresh()}catch(cancel:CancellationException){throw cancel}catch(_:Exception){status="Lijsten niet beschikbaar"}finally{busy=false}}
    SelectValue("Lijst",kind,kinds){if(!busy)kind=it}
    OutlinedButton(enabled=!busy,onClick={perform{refresh()}}){Text("Vernieuwen")}
    items.take(200).forEach {item->OutlinedButton(enabled=!busy,onClick={selected=item;draft=JSONObject(item.getJSONObject("data").toString());key="" to ""}){Text((if(item.getJSONObject("data").optBoolean("checked"))"✓ " else "")+item.getJSONObject("data").getString("name"))}}
    OutlinedButton(enabled=!busy,onClick={selected=null;draft=JSONObject();key="" to ""}){Text("Nieuw item")}
    val definition=schema.optJSONObject(kind)?.optJSONObject("properties") ?: JSONObject()
    definition.keys().asSequence().toList().forEach {name->
        val field=definition.getJSONObject(name)
        if(!field.optBoolean("x-internal")) {
            val value=if(draft.has(name))draft.opt(name) else if(field.has("default"))field.opt("default") else if(field.optString("type")=="integer")field.optInt("minimum",0) else ""
            fun change(value:Any?) {draft=JSONObject(draft.toString()).put(name,value ?: JSONObject.NULL)}
            val title=labels[name] ?: name
            when {
                name=="at" || name=="followup_at" -> DateField(if(name=="at")"Moment" else "Opvolgmoment",value.takeUnless{it==JSONObject.NULL || it==""}?.toString(),name=="followup_at"){change(it)}
                field.has("enum")-> {val array=field.getJSONArray("enum");val choices=(0 until array.length()).map{array.getString(it)};SelectValue(title,value?.toString().takeUnless{it.isNullOrBlank()} ?: choices.first(),choices.associateWith{values[it] ?: it}){change(it)}}
                field.optString("type")=="boolean"->Row {Checkbox(value==true,{change(it)});Text(title)}
                field.optString("type")=="integer"->OutlinedTextField(value?.toString() ?: "",{change(it.toIntOrNull() ?: it)},label={Text(title)},singleLine=true)
                else->OutlinedTextField(value?.takeUnless{it==JSONObject.NULL}?.toString() ?: "",{change(it)},label={Text(title)},singleLine=true,modifier=Modifier.fillMaxWidth())
            }
        }
    }
    Button(enabled=!busy && definition.length()>0,onClick={perform {
        val data=JSONObject(selected?.getJSONObject("data")?.toString() ?: "{}")
        definition.keys().forEach {name->
            val field=definition.getJSONObject(name)
            if(draft.has(name))data.put(name,draft.get(name))
            else if(!data.has(name) && !field.optBoolean("x-internal")) {
                when {field.has("default")->data.put(name,field.get("default"));field.has("enum")->data.put(name,field.getJSONArray("enum").get(0));field.optString("type")=="integer"->data.put(name,field.optInt("minimum",0));name=="at"->data.put(name,ZonedDateTime.now(java.time.ZoneId.of("Europe/Amsterdam")).plusDays(1).withSecond(0).withNano(0).toOffsetDateTime().toString())}
            }
        }
        if(kind=="subscription")data.put("amount",data.optString("amount").replace(',','.'))
        val body=JSONObject().put("kind",kind).put("data",data).put("revision",selected?.getInt("revision") ?: 0)
        val canonical=SettingsDraft.canonical(body)
        if(key.first!=canonical)key=canonical to UUID.randomUUID().toString()
        body.put("request_id",key.second)
        model.butlerRequest(N+"life-items"+(selected?.let{"/"+it.getString("id")} ?: ""),if(selected==null)"POST" else "PUT",body)
        status="Opgeslagen, meneer.";refresh()
    }}){Text("Opslaan")}
    if(selected!=null) {
        OutlinedButton(enabled=!busy,onClick={deletion=true}){Text("Geselecteerd item verwijderen")}
        if(kind in setOf("occasion","routine","application"))OutlinedButton(enabled=!busy,onClick={perform {val item=selected ?: return@perform;model.butlerRequest(N+"life-items/"+item.getString("id")+"/reminder","POST",JSONObject().put("revision",item.getInt("revision")));status="Herinnering ingepland; agenda niet gewijzigd."}}){Text("Herinnering instellen")}
        if(kind=="application") {
            OutlinedTextField(mail,{mail=it},label={Text("Optionele berichtreferentie uit gelezen sollicitatiemail")})
            OutlinedButton(enabled=!busy && mail.isNotBlank(),onClick={perform {val item=selected ?: return@perform;model.butlerRequest(N+"life-items/"+item.getString("id")+"/link-mail","POST",JSONObject().put("revision",item.getInt("revision")).put("message_id",mail));refresh();status="Gelezen reactie gekoppeld."}}){Text("Reactie koppelen")}
        }
    }
    if(deletion)AlertDialog(onDismissRequest={deletion=false},title={Text("Item verwijderen?")},confirmButton={TextButton(onClick={deletion=false;perform {val item=selected ?: return@perform;model.butlerRequest(N+"life-items/"+item.getString("id")+"?revision="+item.getInt("revision"),"DELETE");refresh();status="Verwijderd."}}){Text("Verwijderen")}},dismissButton={TextButton(onClick={deletion=false}){Text("Annuleren")}})
    OutlinedButton(enabled=!busy,onClick={perform{val overview=model.butlerRequest(N+"financial-overview").getJSONObject("monthly_estimate");status="Handmatige abonnementskosten per maand: "+overview.keys().asSequence().joinToString{it+" "+overview.getString(it)}.ifBlank{"nog niets ingevoerd"}+". Geen bankkoppeling."}}){Text("Kostenoverzicht")}
    Text(status)
}

@Composable private fun DeviceControls(state:ScreenState,model:JarvisViewModel) {
    val scope=rememberCoroutineScope();val context=LocalContext.current
    var document by remember {mutableStateOf<JSONObject?>(null)};var busy by remember {mutableStateOf(false)};var status by remember {mutableStateOf("")}
    val location=rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()){status=if(it)"Android-locatietoestemming verleend; schakel delen afzonderlijk in." else "Locatie blijft niet beschikbaar."}
    val notifications=rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()){status=if(it)"Lokale meldingen toegestaan." else "Lees briefings in de app."}
    suspend fun load() {document=model.butlerRequest(N+"device-settings")}
    LaunchedEffect(Unit) {try{load()}catch(_:Exception){status="Apparaattoestemmingen niet opgehaald"}}
    fun save(flag:String,value:Any) {
        val old=document ?: return;if(busy)return;busy=true
        scope.launch {try {
            val settings=JSONObject(old.getJSONObject("settings").toString()).put(flag,value)
            document=model.butlerRequest(N+"device-settings","PUT",JSONObject().put("revision",old.getInt("revision")).put("settings",settings))
            model.presenceRefresh();status="Apparaattoestemming opgeslagen."
        }catch(cancel:CancellationException){throw cancel}catch(_:Exception){status="Niet opgeslagen; vernieuw de apparaatinstellingen."}finally{busy=false}}
    }
    Text("Elke optie geldt uitsluitend voor deze telefoon. Meldingen delen uitsluitend aantallen, geen inhoud. Locatie is optioneel en wordt maximaal 24 uur bewaard.")
    val settings=document?.optJSONObject("settings") ?: JSONObject()
    listOf("presence_allowed" to "Aanwezigheidsstatus delen","status_allowed" to "Batterijstatus delen","notification_allowed" to "Meldingsaantallen delen","location_allowed" to "Laatst bekende locatie delen","handoff_allowed" to "Goedgekeurde opdrachten in telefoonapps klaarzetten","screen_allowed" to "Geselecteerde afbeeldingen mogen worden geanalyseerd").forEach {(key,title)->Row {Checkbox(settings.optBoolean(key),{save(key,it)},enabled=document!=null && !busy);Text(title)}}
    Text("Apps waarvan u meldingsaantallen wilt delen:")
    val allowed=settings.optJSONArray("notification_packages")?.let {array->(0 until array.length()).map{array.getString(it)}} ?: emptyList()
    mapOf("com.whatsapp" to "WhatsApp","org.thoughtcrime.securesms" to "Signal","com.google.android.gm" to "Gmail","com.microsoft.office.outlook" to "Outlook","com.google.android.apps.messaging" to "Google Berichten").forEach {(key,title)->Row {Checkbox(key in allowed,{save("notification_packages",JSONArray(if(it)(allowed+key).distinct() else allowed-key))},enabled=document!=null && !busy);Text(title)}}
    OutlinedButton(onClick={try{context.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))}catch(_:Exception){status="Open Meldingen → Speciale toegang in Android-instellingen."}}){Text("Meldingsaantallen: Android-toegang instellen")}
    OutlinedButton(onClick={location.launch(Manifest.permission.ACCESS_COARSE_LOCATION)}){Text("Optionele Android-locatietoestemming")}
    if(Build.VERSION.SDK_INT>=33)OutlinedButton(onClick={notifications.launch(Manifest.permission.POST_NOTIFICATIONS)}){Text("Lokale meldingen toestaan")}
    Row {Checkbox(state.preferences.backgroundSync,{model.save(state.preferences.copy(backgroundSync=it))});Text("Briefings in achtergrond ophalen (Android kan dit uitstellen; minimaal 15 min)")}
    OutlinedButton(enabled=!busy,onClick={scope.launch{try{load();status="Vernieuwd."}catch(_:Exception){status="Niet opgehaald"}}}){Text("Apparaatinstellingen vernieuwen")}
    Text(status)
}

@Composable private fun IntegrationControls(model:JarvisViewModel) {
    val scope=rememberCoroutineScope();var report by remember {mutableStateOf("")};var busy by remember {mutableStateOf(false)}
    var origin by remember {mutableStateOf("")};var destination by remember {mutableStateOf("")};var distance by remember {mutableStateOf("")};var consumption by remember {mutableStateOf("7")};var price by remember {mutableStateOf("2")}
    fun run(block:suspend()->String) {if(busy)return;busy=true;scope.launch{try{report=block()}catch(cancel:CancellationException){throw cancel}catch(_:Exception){report="Niet beschikbaar; controleer de bronconfiguratie, invoer en uw rechten. Geen gegevens verzonnen."}finally{busy=false}}}
    OutlinedButton(enabled=!busy,onClick={run {
        val data=model.butlerRequest(A+"external")
        "Home Assistant: "+(if(data.getJSONObject("home_assistant").getBoolean("configured"))"geconfigureerd" else "beveiligde configuratie ontbreekt")+"\nRoutes: "+(if(data.getJSONObject("routes").getBoolean("configured"))"geconfigureerd" else "beveiligde sleutel ontbreekt")+"\nCreality Hi/Cloud: geen publieke API geverifieerd. Phone Link: bedienen in de eigen app."
    }}){Text("Integraties controleren")}
    OutlinedButton(enabled=!busy,onClick={run {model.butlerRequest(N+"device-status").objectList("items").joinToString("\n") {item->
        val battery=item.getJSONObject("status").optJSONObject("battery")
        item.getString("name")+": "+(battery?.let {"${it.getInt("value")}% batterij"+(if(it.getBoolean("stale"))" (verouderd)" else "")} ?: "toegestane metadata beschikbaar")
    }.ifBlank{"Geen apparaat deelt momenteel status."}}}){Text("Apparaatstatus ophalen")}
    OutlinedTextField(origin,{origin=it},label={Text("Vertrekplaats")});OutlinedTextField(destination,{destination=it},label={Text("Bestemming")})
    OutlinedButton(enabled=!busy,onClick={run {val data=model.butlerRequest(A+"route-cities","POST",JSONObject().put("origin",origin).put("destination",destination));distance=data.getDouble("distance_km").toString();"${data.getString("origin")} → ${data.getString("destination")}: ${data.getDouble("distance_km")} km, ${kotlin.math.round(data.getDouble("duration_seconds")/60).toInt()} minuten. Geen live verkeer."}}){Text("Route opvragen")}
    OutlinedTextField(distance,{distance=it},label={Text("Afstand (km)")});OutlinedTextField(consumption,{consumption=it},label={Text("Verbruik (liter / 100 km)")});OutlinedTextField(price,{price=it},label={Text("Zelf ingevoerde literprijs (€)")})
    OutlinedButton(enabled=!busy,onClick={run {val data=model.butlerRequest(A+"trip-cost","POST",JSONObject().put("distance_km",distance.replace(',','.')).put("liters_per_100km",consumption.replace(',','.')).put("price_per_liter",price.replace(',','.')));"Geschat: ${data.getString("liters")} liter, € ${data.getString("estimated_fuel_cost_eur")}. Eigen prijs; geen actuele pompprijs."}}){Text("Ritkosten berekenen")}
    Text(report)
}

@Composable fun ImageContextScreen(state:ScreenState,model:JarvisViewModel) {
    val scope=rememberCoroutineScope();val context=LocalContext.current
    var document by remember {mutableStateOf<JSONObject?>(null)};var image by remember {mutableStateOf<ByteArray?>(null)}
    var question by remember {mutableStateOf("Wat valt u op en kunt u mij hierbij helpen?")};var report by remember {mutableStateOf("")};var busy by remember {mutableStateOf(false)}
    LaunchedEffect(state.naturalSettings) {image=null;try{document=model.butlerRequest(N+"settings")}catch(_:Exception){report="Beeldinstellingen niet opgehaald"}}
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) {uri->if(uri!=null)scope.launch {
        busy=true;image=null
        try {val device=model.butlerRequest(N+"device-settings");val fresh=model.butlerRequest(N+"settings")
            require(device.getJSONObject("settings").optBoolean("screen_allowed") && fresh.getJSONObject("settings").getJSONObject("vision").optBoolean("enabled"))
            document=fresh;image=nl.jarvis.mobile.device.SelectedImage.read(context,uri);report="Controleer uw voorbeeld op privégegevens, meneer."
        }catch(cancel:CancellationException){throw cancel}catch(_:Exception){report="Kies een ondersteunde afbeelding en schakel beeldanalyse en de aparte apparaattoestemming bewust in."}finally{busy=false}
    }}
    val vision=document?.optJSONObject("settings")?.optJSONObject("vision")
    Text("U kiest zelf één afbeelding. JARVIS neemt geen scherm op en bewaart de afbeelding niet. Provider: ${vision?.optString("provider") ?: "nog niet opgehaald"}. Daglimiet: ${vision?.optInt("daily_requests") ?: 0}.")
    OutlinedButton(enabled=!busy,onClick={picker.launch("image/*")}){Text("Afbeelding kiezen en controleren")}
    image?.let {bytes->val bitmap=remember(bytes){BitmapFactory.decodeByteArray(bytes,0,bytes.size)};if(bitmap!=null)Image(bitmap.asImageBitmap(),"Geselecteerd voorbeeld",Modifier.fillMaxWidth().heightIn(max=280.dp))}
    OutlinedTextField(question,{question=it.take(600)},label={Text("Uw vraag over deze afbeelding")},modifier=Modifier.fillMaxWidth())
    Button(enabled=!busy && image!=null && document!=null,onClick={
        val bytes=image ?: return@Button;val revision=document!!.getInt("revision");busy=true
        scope.launch {try {
            val data=model.butlerImage(JSONObject().put("request_id",UUID.randomUUID().toString()).put("settings_revision",revision).put("image",Base64.encodeToString(bytes,Base64.NO_WRAP)).put("question",question))
            val result=data.getJSONObject("report")
            report=data.getString("intro")+"\n"+listOf("observations" to "Waarnemingen","uncertainty" to "Onzekerheden","suggestions" to "Suggesties").joinToString("\n\n") {(key,title)->title+"\n"+(0 until result.getJSONArray(key).length()).joinToString("\n"){result.getJSONArray(key).getString(it)}}
        }catch(cancel:CancellationException){throw cancel}catch(_:Exception){report="Analyse niet bevestigd. Controleer provider, apparaat-/cloudtoestemming en daglimiet. Geen automatische nieuwe poging."}finally{image=null;busy=false}}
    }){Text("Dit gecontroleerde voorbeeld verzenden")}
    OutlinedButton(onClick={image=null}){Text("Voorbeeld verwijderen")}
    Text(report)
}
