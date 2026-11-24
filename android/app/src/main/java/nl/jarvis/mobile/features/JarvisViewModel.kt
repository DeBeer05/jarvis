package nl.jarvis.mobile.features

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.*
import nl.jarvis.mobile.JarvisApplication
import nl.jarvis.mobile.BuildConfig
import nl.jarvis.mobile.core.*
import nl.jarvis.mobile.data.Preferences
import nl.jarvis.mobile.voice.AudioClient
import nl.jarvis.mobile.voice.ConversationSession
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

data class Line(val role: String, val text: String)
data class Conversation(val id: String, val title: String)
data class ScreenState(
    val preferences: Preferences = Preferences(), val screen: String = "Welkom", val connection: Connection = Connection(),
    val messages: List<Line> = emptyList(), val history: List<Conversation> = emptyList(), val conversation: String? = null,
    val busy: Boolean = false, val recording: Boolean = false, val level: Float = 0f, val voiceStatus: String = "Klaar om te luisteren",
    val transcript: String = "", val error: String = "", val pairCode: String = "", val pairUrl: String = "",
    val device: String = "Nog niet gekoppeld", val provider: String = "auto", val model: String = "", val notificationStatus: String = "Lokale testmeldingen",
    val automations: String = "", val automationResult: String = "",
    val naturalSettings: String = "", val naturalSchema: String = "", val naturalMemory: String = "",
    val naturalSummaries: String = "", val naturalStatus: String = "",val conversationState: String="STANDBY"
)
class JarvisViewModel(application: Application,val audio: AudioClient): AndroidViewModel(application) {
    constructor(application: Application):this(application,AudioClient(application))
    private val graph = (application as JarvisApplication).graph
    private val mutable = MutableStateFlow(ScreenState())
    val state = mutable.asStateFlow()
    private var currentApi: nl.jarvis.mobile.data.JarvisApi? = null
    private var initialized = false; private var foreground = false
    private var generation = 0
    private var sendJob: Job? = null; private var audioJob: Job? = null; private var pairJob: Job? = null
    private var requestId: String? = null
    private val connection = ConnectionManager(application, viewModelScope) { currentApi }
    private var voiceConversationActive=false;private var voiceStarted=0L;private var lastVoice=0L
    private var followupJob: Job?=null
    private val conversationSession=ConversationSession(viewModelScope,{currentApi},{foreground},{voiceProblem(it)},{lease -> mutable.update {it.copy(conversationState=lease?.state ?: "STANDBY")}})

    private fun naturalConfig(): JSONObject?=try {JSONObject(mutable.value.naturalSettings).getJSONObject("settings")}catch(_:Exception){null}
    private fun naturalVoice()=naturalConfig()?.optJSONObject("conversations")
    private fun naturalEnabled()=naturalVoice()?.optBoolean("enabled")==true
    private fun continuousVoice()=voiceConversationActive&&naturalVoice()?.optBoolean("continuous")==true
    private fun voiceSpeed()=(naturalConfig()?.optJSONObject("voice")?.optDouble("speed")?.toFloat() ?: mutable.value.preferences.speed).coerceIn(.7f,1.5f)
    private fun voiceVolume()=(naturalConfig()?.optJSONObject("voice")?.optDouble("volume")?.toFloat() ?: 1f).coerceIn(0f,1f)
    private fun activateVoice() {if(!voiceConversationActive) {
        check(audio.beginConversation()) {"Audio wordt door een ander gesprek gebruikt"}
        voiceStarted=System.nanoTime();voiceConversationActive=true
    };lastVoice=System.nanoTime()}
    private fun isEnding(text: String): Boolean {
        val phrases=naturalVoice()?.optJSONArray("ending_phrases") ?: return false
        fun normalized(value:String)=value.lowercase().replace(Regex("[^\\p{L}\\p{N}\\s]"),"").trim()
        return (0 until phrases.length()).any {normalized(phrases.getString(it))==normalized(text)}
    }
    private fun voiceProblem(error: Throwable) {if(error is CancellationException)return;stop();problem(error)}
    private fun continueVoice(responseFinished: Boolean=false) {
        if(responseFinished)lastVoice=System.nanoTime()
        followupJob?.cancel()
        if(!foreground || !voiceConversationActive)return
        followupJob=viewModelScope.launch {try {
            if(naturalEnabled())conversationSession.listening()
            val config=naturalVoice() ?: return@launch
            if(!continuousVoice() || !config.optBoolean("auto_listen",true))return@launch
            val now=System.nanoTime()
            if((now-voiceStarted)/1_000_000_000>=config.optLong("maximum_seconds",1800) || config.optBoolean("automatic_end",true)&&(now-lastVoice)/1_000_000_000>=config.optLong("inactivity_seconds",90)) {
                stop();mutable.update {it.copy(voiceStatus="Standby")};return@launch
            }
            delay(450)
            if(foreground&&voiceConversationActive)captureVoice(false)
        } catch(error:Exception){voiceProblem(error)}}
    }
    init {
        audio.focusLost={viewModelScope.launch {stop();message("Audiofocus verloren; de microfoon en spraak zijn gestopt")}}
        viewModelScope.launch { graph.settings.values.collect { preferences ->
            val changed = currentApi?.endpoint?.origin != preferences.origin
            if (changed) {
                stop(); pairJob?.cancel(); connection.stop()
                currentApi = try { graph.api(preferences.origin) } catch (_: IllegalArgumentException) { null }
                mutable.update { it.copy(naturalSettings="", naturalSchema="", naturalMemory="", naturalSummaries="", naturalStatus="", automations="", automationResult="", messages=emptyList(), history=emptyList(), conversation=null, pairCode="", pairUrl="") }
            }
            mutable.update { it.copy(preferences=preferences, screen=if (!initialized && currentApi?.hasCredential() == true) "Chat" else it.screen) }
            initialized = true
            if (foreground) connection.start(preferences.automatic)
        } }
        viewModelScope.launch { connection.values.collect { status ->
            val was = mutable.value.connection.authenticated
            mutable.update { it.copy(connection=status) }
            if (status.authenticated && !was) { history(); device(); naturalRefresh() }
            if (!status.authenticated && was) stop()
            if (status.online && !status.authenticated && currentApi?.hasCredential() != true) {
                currentApi?.let { graph.cache.clear(it.endpoint.origin) }
                mutable.update { it.copy(naturalSettings="", naturalSchema="", naturalMemory="", naturalSummaries="", naturalStatus="", automations="", automationResult="", messages=emptyList(), history=emptyList(), conversation=null) }
            }
        } }
    }
    fun navigate(screen: String) { mutable.update { it.copy(screen=screen, error="") }; if (screen=="Gesprekken") history(); if (screen=="Apparaten" || screen=="Account") device(); if(screen=="Automatiseringen") automationRefresh(); if(screen=="Instellingen") naturalRefresh() }

    fun naturalRequest(path: String, method: String="GET", body: JSONObject?=null, done: ((JSONObject)->Unit)?=null) {
        val api=currentApi ?: return; val epoch=generation
        if(!mutable.value.connection.authenticated) return message("Log eerst in en koppel dit apparaat")
        viewModelScope.launch { try {
            val data=api.json("/api/v1/natural$path",method,body)
            if(currentApi===api && epoch==generation && api.hasCredential()) done?.invoke(data)
        } catch(cancel: CancellationException) { throw cancel }
          catch(error: Exception) { if(currentApi===api && epoch==generation) {
            mutable.update {it.copy(naturalStatus="Niet opgeslagen/opgehaald. Controleer de invoer; bij een wijzigingsconflict moet je eerst vernieuwen. Je invoer blijft staan.")};problem(error)
        } } }
    }
    fun naturalRefresh() {
        if(!mutable.value.connection.authenticated)return
        if(mutable.value.naturalSchema.isBlank()) naturalRequest("/settings/schema") {data -> mutable.update {it.copy(naturalSchema=data.toString())}}
        naturalRequest("/settings") {data -> mutable.update {it.copy(naturalSettings=data.toString(),naturalStatus="Gesynchroniseerd · versie ${data.getInt("revision")}")}}
    }
    fun saveNaturalSettings(settings: String,revision: Int) {
        try { naturalRequest("/settings","PUT",JSONObject().put("revision",revision).put("settings",JSONObject(settings))) {data -> mutable.update {it.copy(naturalSettings=data.toString(),naturalStatus="Opgeslagen · versie ${data.getInt("revision")}")}} }
        catch(_:Exception) {message("Controleer de instellingen")}
    }
    fun resetNaturalCategory(category: String,revision: Int) {
        naturalRequest("/settings/reset","POST",JSONObject().put("revision",revision).put("category",category)) {data -> mutable.update {it.copy(naturalSettings=data.toString(),naturalStatus="Standaardwaarden opgeslagen")}}
    }
    fun exportNatural(path: String,done: (String)->Unit) {naturalRequest(path) {data -> done(data.toString(2))}}
    fun importNatural(text: String,revision: Int) {
        try { val document=JSONObject(text);require(document.optString("scope")=="user")
            naturalRequest("/settings/import","POST",JSONObject().put("revision",revision).put("document",document)) {data -> mutable.update {it.copy(naturalSettings=data.toString(),naturalStatus="Instellingen geïmporteerd")}}
        } catch(_:Exception) {message("Ongeldig instellingenbestand")}
    }
    fun naturalMemory(query: String="",category: String="") {
        val body=JSONObject().put("query",query);if(category.isNotBlank())body.put("category",category)
        naturalRequest("/memory/search","POST",body) {data -> mutable.update {it.copy(naturalMemory=data.toString())}}
        naturalRequest("/summaries") {data -> mutable.update {it.copy(naturalSummaries=data.toString())}}
    }
    private fun memoryChanged() {if(mutable.value.busy || mutable.value.voiceStatus=="JARVIS spreekt")stop();naturalMemory()}
    fun naturalMemorySave(data: JSONObject,id: String?=null) {naturalRequest(if(id==null)"/memory" else "/memory/$id",if(id==null)"POST" else "PUT",data) {memoryChanged()}}
    fun naturalMemoryDelete(id: String) {naturalRequest("/memory/$id","DELETE") {memoryChanged()}}
    fun naturalMemoryClear() {naturalRequest("/memory/clear","POST",JSONObject().put("confirmed",true)) {memoryChanged()}}
    fun naturalSummarySave(id: String,text: String,revision: Int) {naturalRequest("/summaries/$id","PUT",JSONObject().put("revision",revision).put("content",text)) {naturalMemory()}}

    private var automationJob: Job? = null
    private val seenNotifications=mutableSetOf<String>()
    fun automationRequest(path: String, method: String="GET", body: JSONObject?=null, done: ((JSONObject)->Unit)?=null) {
        val api=currentApi ?: return; val epoch=generation
        viewModelScope.launch { try {
            val data=api.json("/api/v1/automation$path",method,body)
            if(currentApi===api && epoch==generation && api.hasCredential()) {
                if(done!=null) done(data) else mutable.update { it.copy(automationResult=data.toString(2)) }
            }
        } catch(error: Exception) { if(currentApi===api && epoch==generation) {
            if(error is MobileError && error.status==401) problem(error)
            else message(if(error is MobileError) error.message ?: "Automatiseringsverzoek mislukt" else "Automatiseringsverzoek mislukt. Controleer verbinding en actiegegevens.")
        } } }
    }
    fun automationRefresh() {
        if(!mutable.value.connection.authenticated || "automation:read" !in mutable.value.connection.permissions) {
            mutable.update { it.copy(automationResult="Log in en laat de eigenaar automatiseringsrechten voor dit apparaat verlenen.") };return
        }
        automationRequest("") { data ->
        mutable.update { it.copy(automations=data.toString()) }
        val origin=currentApi?.endpoint?.origin ?: return@automationRequest;val epoch=generation
        viewModelScope.launch {
            val floor=graph.settings.notificationCursor(origin);var latest=floor
            if(currentApi?.endpoint?.origin!=origin || generation!=epoch) return@launch
            val notes=data.optJSONArray("notifications") ?: JSONArray()
            for(i in 0 until notes.length()) { val note=notes.getJSONObject(i);latest=maxOf(latest,note.getDouble("at"))
                if(note.getDouble("at")>floor && seenNotifications.add(note.getString("id")) && note.getString("category") in mutable.value.preferences.categories) graph.notifications.show(note.getString("category"),"Automatiseringen")
            }
            graph.settings.notificationSeen(origin,latest)
        }
    } }
    fun automationSubmit(tool: String, text: String) {
        try { val body=JSONObject().put("tool",tool).put("input",JSONObject(text)).put("idempotency_key",UUID.randomUUID().toString())
            automationRequest("/jobs","POST",body) { automationRefresh() }
        } catch (_: Exception) { message("Controleer de JSON-actiegegevens") }
    }
    fun automationDecide(id: String, approve: Boolean) {
        automationRequest("/jobs/$id/challenge","POST") { challenge ->
            automationRequest("/jobs/$id/decision","POST",JSONObject().put("token",challenge.getString("token")).put("approve",approve)) { automationRefresh() }
        }
    }
    fun automationControl(id: String,status: String) { automationRequest("/jobs/$id/control","POST",JSONObject().put("status",status)) { automationRefresh() } }
    fun active(value: Boolean) { foreground = value; if (value) {
        connection.start(mutable.value.preferences.automatic)
        automationJob?.cancel();automationJob=viewModelScope.launch { while(isActive) {
            if(mutable.value.connection.authenticated) naturalRefresh()
            if(mutable.value.connection.authenticated && "automation:read" in mutable.value.connection.permissions) automationRefresh()
            delay(30000)
        } }
    } else { automationJob?.cancel();stop(); pairJob?.cancel(); connection.stop() } }
    fun reconnect() { connection.checkNow() }
    private fun problem(error: Throwable) {
        if (error is CancellationException) return
        mutable.update { it.copy(error=if (error is MobileError) error.message ?: "Verzoek mislukt" else if (error is IllegalArgumentException) error.message ?: "Ongeldige instelling" else "Verbinding of audio onderbroken. Controleer server en apparaten.") }
        if (error is MobileError && error.status == 401) {
            stop(); currentApi?.forget(); currentApi?.let { api -> viewModelScope.launch { graph.cache.clear(api.endpoint.origin) } }
            mutable.update { it.copy(naturalSettings="", naturalSchema="", naturalMemory="", naturalSummaries="", naturalStatus="", automations="", automationResult="", connection=Connection(true,false,"Opnieuw koppelen nodig"), messages=emptyList(), history=emptyList(), conversation=null, screen="Inloggen") }
        }
    }
    fun message(text: String) { mutable.update { it.copy(error=text) } }
    fun save(preferences: Preferences) { viewModelScope.launch {
        try { Endpoint.parse(preferences.origin, BuildConfig.DEBUG); graph.settings.save(preferences); mutable.update { it.copy(error="Instellingen opgeslagen") } } catch (error: Exception) { problem(error) }
    } }
    fun beginPair(username: String = "", password: String = "") {
        val api = currentApi ?: return message("Stel eerst een geldig serveradres in")
        pairJob?.cancel(); stop()
        api.invalidatePendingAuth()
        pairJob = viewModelScope.launch {
            val epoch = generation; val verifier = Proof.verifier()
            try {
                val body = JSONObject().put("device_name", "JARVIS Android").put("code_challenge", Proof.challenge(verifier))
                val request = if (username.isNotBlank() || password.isNotBlank()) {
                    body.put("username", username).put("password", password)
                    api.json("/api/v1/auth/android-login", "POST", body, false)
                } else {
                    body.put("device_type", "android").put("code_challenge_method", "S256")
                        .put("scopes", JSONArray(listOf("chat:read", "chat:write", "chat:delete", "status:read")))
                    api.json("/api/v1/pairing/requests", "POST", body, false)
                }
                mutable.update { it.copy(screen="Koppelen", pairCode=request.getString("user_code"), pairUrl=api.endpoint.origin + "/security", error="") }
                var interval = request.getLong("interval").coerceIn(5,30)
                val deadline = System.nanoTime() + request.getLong("expires_in").coerceAtMost(600) * 1_000_000_000
                while (System.nanoTime() < deadline && epoch == generation) {
                    delay(interval * 1000)
                    try {
                        api.finishPair(JSONObject().put("grant_type", "urn:ietf:params:oauth:grant-type:device_code").put("device_code", request.getString("device_code")).put("code_verifier", verifier))
                        mutable.update { it.copy(pairCode="", pairUrl="", screen="Chat") }; reconnect(); return@launch
                    } catch (error: MobileError) {
                        if (error.code == "slow_down") interval = (interval + 5).coerceAtMost(30)
                        else if (error.code != "authorization_pending") throw error
                    }
                }
                message("Koppelcode verlopen; vraag een nieuwe code aan")
            } catch (error: Exception) { problem(error) }
        }
    }
    fun history() {
        val api = currentApi ?: return
        if(mutable.value.connection.authenticated && "chat:read" !in mutable.value.connection.permissions) return
        val epoch = generation
        viewModelScope.launch { try {
            val response = if (mutable.value.connection.authenticated) {
                api.json("/api/v1/chat/conversations?limit=100&offset=0").also { graph.cache.put(api.endpoint.origin, "list", it.toString()) { currentApi===api && generation==epoch && api.hasCredential() } }
            } else if (api.hasCredential()) graph.cache.get(api.endpoint.origin, "list")?.let { JSONObject(it) } else null
            val items = response?.optJSONArray("items") ?: JSONArray()
            if (currentApi === api && generation==epoch && api.hasCredential()) mutable.update { it.copy(history=(0 until items.length()).map { i -> val row=items.getJSONObject(i); Conversation(row.getString("id"), row.getString("title")) }) }
        } catch (error: Exception) { problem(error) } }
    }
    fun open(id: String) {
        if (mutable.value.busy) return
        stop()
        val api = currentApi ?: return
        val epoch = generation
        viewModelScope.launch { try {
            val response = if (mutable.value.connection.authenticated) api.json("/api/v1/chat/conversations/$id").also { graph.cache.put(api.endpoint.origin, id, it.toString()) { currentApi===api && generation==epoch && api.hasCredential() } }
                else if (api.hasCredential()) graph.cache.get(api.endpoint.origin, id)?.let { JSONObject(it) } else null
            if (response == null) return@launch message("Dit gesprek is niet lokaal beschikbaar")
            val turns=response.getJSONArray("turns"); val lines=mutableListOf<Line>()
            repeat(turns.length()) { index -> val turn=turns.getJSONObject(index); lines += Line("JIJ", turn.getString("user_text")); lines += Line("JARVIS", turn.getString("assistant_text")) }
            if (currentApi === api && generation==epoch && api.hasCredential()) mutable.update { it.copy(messages=lines, conversation=id, screen="Chat") }
        } catch (error: Exception) { problem(error) } }
    }
    fun delete(id: String) { val api=currentApi ?: return; viewModelScope.launch { try { api.json("/api/v1/chat/conversations/$id", "DELETE"); graph.cache.clear(api.endpoint.origin); if (mutable.value.conversation==id) newConversation(); history() } catch (error: Exception) { problem(error) } } }
    fun newConversation() { stop(); mutable.update { it.copy(conversation=null, messages=emptyList(), transcript="", screen="Chat") } }
    fun provider(value: String) { mutable.update { it.copy(provider=value) } }
    fun send(text: String, speak: Boolean = false) {
        if(text.isBlank() || text.length>8000 || mutable.value.busy || !mutable.value.connection.authenticated || "chat:write" !in mutable.value.connection.permissions)return
        cancelTurn(false);val api=currentApi ?: return
        val epoch=generation;val request=UUID.randomUUID().toString();requestId=request
        val conversation=mutable.value.conversation;val narrate=speak&&mutable.value.preferences.voiceOutput
        val speed=voiceSpeed();val volume=voiceVolume();val succeeded=java.util.concurrent.atomic.AtomicBoolean(false)
        mutable.update {it.copy(busy=true,messages=it.messages+Line("JIJ",text)+Line("JARVIS",""),error="",voiceStatus="JARVIS denkt…")}
        val queue=Channel<String>(32);val segments=SentenceBuffer()
        if(narrate)audioJob=viewModelScope.launch {
            try {
                for(sentence in queue) {
                    val wav=api.synthesize(sentence,speed);ensureActive();if(epoch!=generation)return@launch
                    mutable.update {it.copy(voiceStatus="JARVIS spreekt")};audio.play(wav,mutable.value.preferences.outputDevice,volume)
                }
                if(epoch==generation) {mutable.update {it.copy(voiceStatus="Klaar om te luisteren")};if(succeeded.get())continueVoice(true)}
            }catch(error:Exception){if(epoch==generation)voiceProblem(error)}
        }
        sendJob=viewModelScope.launch {
            try {
                val lease=if(speak&&naturalEnabled())conversationSession.prepare(conversation) else null
                if(!speak) {voiceConversationActive=false;conversationSession.endBeforeText();audio.endConversation()}
                ensureActive();if(epoch!=generation)return@launch
                lease?.let {mutable.update {state->state.copy(conversation=it.conversation)}}
                val body=JSONObject().put("message",text).put("provider",mutable.value.provider).put("request_id",request)
                (lease?.conversation ?: conversation)?.let {body.put("conversation_id",it)}
                if(speak)body.put("channel","voice")
                lease?.let {body.put("session_epoch",it.epoch)}
                api.stream(body) {event -> if(epoch==generation&&currentApi===api)when(event.optString("type")) {
                    "meta" -> mutable.update {it.copy(conversation=event.getString("conversation_id"))}
                    "provider" -> mutable.update {it.copy(model=event.getString("provider")+" · "+event.getString("model"))}
                    "delta" -> {
                        val delta=event.getString("text")
                        mutable.update {it.copy(messages=it.messages.dropLast(1)+it.messages.last().copy(text=it.messages.last().text+delta))}
                        if(narrate)segments.add(delta).forEach {check(queue.trySend(it).isSuccess) {"Spraakbuffer vol"}}
                    }
                    "error" -> message(event.optString("message","Antwoord mislukt"))
                    "done" -> {
                        succeeded.set(event.getString("status")=="completed")
                        if(succeeded.get()&&narrate)segments.add("",true).forEach {check(queue.trySend(it).isSuccess) {"Spraakbuffer vol"}}
                        else if(!succeeded.get()) {audioJob?.cancel();audio.stop();voiceConversationActive=false;conversationSession.end()}
                    }
                }}
                if(epoch==generation) {requestId=null;mutable.update {it.copy(busy=false)};history();if(speak&&!narrate&&succeeded.get())continueVoice(true)}
            }catch(error:Exception){if(epoch==generation)voiceProblem(error)}finally{queue.close()}
        }
    }
    fun ptt() {captureVoice(true)}
    private fun captureVoice(manual: Boolean) {
        if(!foreground)return
        if(mutable.value.recording) {if(manual)audio.finishRecording();return}
        if(!mutable.value.connection.authenticated)return message("Log in en koppel je telefoon voordat je praat")
        if("chat:write" !in mutable.value.connection.permissions)return message("Dit apparaat mag geen chat- of spraakopdrachten versturen")
        cancelTurn(false);if(manual&&naturalEnabled())try {activateVoice()}catch(error:Exception){voiceProblem(error);return}
        val epoch=generation;val api=currentApi ?: return
        val listening=naturalConfig()?.optJSONObject("listening")
        mutable.update {it.copy(recording=true,voiceStatus="Ik luister…",error="")}
        audioJob=viewModelScope.launch {
            try {
                val wav=audio.record(mutable.value.preferences.inputDevice,threshold=listening?.optDouble("vad_threshold")?.toFloat() ?: .015f,
                    silenceMs=if(listening?.optBoolean("adaptive")==true)listening.optInt("thinking_pause_ms",2500) else listening?.optInt("normal_silence_ms",1200) ?: 1200,
                    maximumSeconds=listening?.optInt("maximum_listen_seconds",60) ?: 60,echo=listening?.optBoolean("echo_suppression")==true,noise=listening?.optBoolean("noise_suppression")==true) {level -> if(epoch==generation)mutable.update {it.copy(level=level,voiceStatus=if(level>.12f)"Ik hoor je…" else "Ik luister…")}}
                if(epoch!=generation)return@launch
                mutable.update {it.copy(recording=false,voiceStatus="Spraak verwerken…")}
                if(wav.isEmpty()) {mutable.update {it.copy(voiceStatus="Geen duidelijke spraak gehoord")};audioJob=null;if(continuousVoice())continueVoice();return@launch}
                val text=api.transcribe(wav)
                if(epoch==generation) {
                    mutable.update {it.copy(transcript=text)};audioJob=null
                    if(voiceConversationActive&&isEnding(text)) {stop();mutable.update {it.copy(voiceStatus="Standby")};return@launch}
                    if(text.isBlank()) {if(continuousVoice())continueVoice();return@launch}
                    lastVoice=System.nanoTime();send(text,true)
                }
            }catch(error:Exception){if(epoch==generation)voiceProblem(error)}
        }
    }
    fun takeOverConversation() {
        if(!foreground||!mutable.value.connection.authenticated)return message("Open de app en log in voordat je een gesprek overneemt")
        if(mutable.value.busy)return
        cancelTurn(false);val epoch=generation
        audioJob=viewModelScope.launch {try {
            val lease=conversationSession.prepare(mutable.value.conversation,true);conversationSession.listening()
            if(epoch==generation) {mutable.update {it.copy(conversation=lease.conversation)};activateVoice();audioJob=null;captureVoice(false)}
        }catch(error:Exception){voiceProblem(error)}}
    }
    fun sample() {
        if (!mutable.value.connection.authenticated) return message("Log eerst in")
        stop(); val api=currentApi ?: return; val epoch=generation
        audioJob=viewModelScope.launch { try {
            mutable.update { it.copy(voiceStatus="Stem voorbereiden…") }
            val wav=api.synthesize("Hallo, ik ben Jarvis. Dit is mijn Nederlandse stem.", mutable.value.preferences.speed)
            if (epoch==generation) { mutable.update { it.copy(voiceStatus="JARVIS spreekt") }; audio.play(wav,mutable.value.preferences.outputDevice); mutable.update { it.copy(voiceStatus="Klaar om te luisteren") } }
        } catch (error: Exception) { if(epoch==generation) voiceProblem(error) } }
    }
    fun stop() {cancelTurn(true)}
    private fun cancelTurn(endConversation: Boolean) {
        followupJob?.cancel();followupJob=null
        if(endConversation) {voiceConversationActive=false;conversationSession.end();audio.endConversation()}
        generation++; audio.stop(); currentApi?.stop(); sendJob?.cancel(); audioJob?.cancel()
        val request=requestId; requestId=null
        val api=currentApi
        if (request!=null && api!=null) viewModelScope.launch { try { api.json("/api/v1/chat/requests/$request/cancel", "POST") } catch (_: Exception) { /* disconnect also cancels server work */ } }
        mutable.update { it.copy(busy=false, recording=false, level=0f, voiceStatus="Gestopt") }
    }
    fun device() { val api=currentApi ?: return; if(!mutable.value.connection.authenticated) return
        viewModelScope.launch { try { val result=api.json("/api/v1/auth/device"); mutable.update { it.copy(device=result.getString("name") + "\n" + result.getString("id") + "\n" + result.getJSONArray("permissions").toString()) } } catch (error: Exception) { problem(error) } }
    }
    fun logout(revoke: Boolean = false) { val api=currentApi ?: return; stop(); pairJob?.cancel()
        viewModelScope.launch { try { api.json("/api/v1/mobile/push", "DELETE"); api.json(if(revoke) "/api/v1/auth/disconnect" else "/api/v1/auth/logout", "POST") }
            catch (_: Exception) { message("Lokaal uitgelogd. Trek de sessie bij onbereikbare server ook in via de eigenaarinterface.") }
            finally { api.forget(); graph.vault.drop("fcm-pending"); graph.cache.clear(api.endpoint.origin); mutable.update { it.copy(naturalSettings="", naturalSchema="", naturalMemory="", naturalSummaries="", naturalStatus="", automations="", automationResult="", messages=emptyList(), history=emptyList(), conversation=null, screen="Inloggen", device="Niet gekoppeld") }; reconnect() } }
    }
    fun testNotification(category: String) { if(category in mutable.value.preferences.categories) graph.notifications.show(category) }
    fun firebase(enabled: Boolean) {
        viewModelScope.launch {
            if (enabled && !graph.notifications.enableFirebase()) return@launch message("Firebase-configuratie ontbreekt; lokale testmeldingen werken wel")
            if(!enabled) {
                graph.notifications.disableFirebase()
                try { currentApi?.json("/api/v1/mobile/push","DELETE") } catch (_: Exception) { /* local delivery is already disabled */ }
            }
            graph.settings.save(mutable.value.preferences.copy(firebaseEnabled=enabled))
            mutable.update { it.copy(notificationStatus=if(enabled) "Registratie voorbereid; externe bezorging nog niet getest" else "Lokale testmeldingen") }
        }
    }
    override fun onCleared() { stop(); connection.stop(); super.onCleared() }
}
