package nl.jarvis.mobile.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import nl.jarvis.mobile.core.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.coroutines.coroutineContext

class JarvisApi(val endpoint: Endpoint, private val vault: SecretVault) {
    private class SendTrace { val sent = AtomicBoolean(false) }
    private val http = OkHttpClient.Builder().connectTimeout(5, TimeUnit.SECONDS).readTimeout(110, TimeUnit.SECONDS)
        .connectionPool(ConnectionPool(3, 2, TimeUnit.SECONDS)) // below Uvicorn's 5-second idle timeout
        .callTimeout(120, TimeUnit.SECONDS).followRedirects(false).followSslRedirects(false).retryOnConnectionFailure(false)
        .eventListenerFactory { object: EventListener() { override fun requestHeadersStart(call: Call) { call.request().tag(SendTrace::class.java)?.sent?.set(true) } } }.build()
    private val rotation = Mutex()
    private val credentialState = Any()
    @Volatile private var access = ""
    @Volatile private var deadline = 0L
    @Volatile var generation = 0
        private set
    @Volatile private var streamCall: Call? = null
    @Volatile private var transcriptionCall: Call? = null
    @Volatile private var synthesisCall: Call? = null
    private fun make(path: String, method: String, body: RequestBody?, bearer: String? = null): Call {
        require(path.startsWith("/api/") || path == "/health")
        val request = Request.Builder().url(endpoint.origin + path).method(method, body).tag(SendTrace::class.java, SendTrace())
        bearer?.let { request.header("Authorization", "Bearer $it") }
        return http.newCall(request.build())
    }
    private fun error(response: Response): Nothing {
        val raw=try {response.peekBody(8192).string()}catch(_:Exception){""}
        val code=try {JSONObject(raw).optJSONObject("error")?.optString("code")}catch(_:Exception){null}
        if (response.request.url.encodedPath == "/api/v1/pairing/token") {
            if (code in setOf("authorization_pending", "slow_down")) throw MobileError(code!!, response.code, "Wacht op goedkeuring door de eigenaar")
        }
        if (response.code == 401) forget()
        if(response.code==409 && code in setOf("conversation_busy","duplicate_request"))throw MobileError(code!!,409,"Het vorige antwoord wordt nog afgesloten. Wacht even en druk opnieuw op de spreekknop; je hoeft het gesprek niet over te nemen.")
        val message = when(response.code) { 401 -> "Log opnieuw in of koppel dit apparaat opnieuw"; 403 -> "Dit apparaat heeft geen toestemming"; 409 -> "Gegevens of spraaksessie elders gewijzigd. Vernieuw eerst of neem het gesprek expliciet over"; 422 -> "Controleer de invoer en de toegestane waarden"; 429 -> "Te veel verzoeken; wacht even"; 503 -> "Server of spraakengine niet beschikbaar"; else -> "Serververzoek mislukt (${response.code})" }
        throw MobileError("http_${response.code}", response.code, message)
    }
    private fun read(response: Response, limit: Int = 2_000_000): ByteArray {
        if (!response.isSuccessful) error(response)
        val source = response.body?.source() ?: throw MobileError("protocol", message="Leeg serverantwoord")
        val buffer = okio.Buffer()
        while (true) {
            val count = source.read(buffer, minOf(8192L, limit + 1L - buffer.size))
            if (count == -1L) break
            if (buffer.size > limit) throw MobileError("size", message="Serverantwoord te groot")
        }
        return buffer.readByteArray()
    }
    private fun install(data: JSONObject, expected: Int) = synchronized(credentialState) {
        if (expected != generation) throw MobileError("cancelled", message="Inloggen geannuleerd")
        val refresh = data.getString("refresh_token"); val token = data.getString("access_token")
        require(refresh.length in 32..128 && token.length in 32..128)
        vault.put(endpoint.origin, refresh); access = token
        deadline = System.nanoTime() + data.getLong("expires_in").coerceIn(0, 900) * 1_000_000_000
    }
    private suspend fun bearer(): String = rotation.withLock {
        if (access.isNotEmpty() && System.nanoTime() < deadline - 40_000_000_000) return@withLock access
        val (expected, previous) = synchronized(credentialState) {
            val old = vault.get(endpoint.origin) ?: throw MobileError("login", 401, "Log in om verder te gaan")
            vault.drop(endpoint.origin) // ambiguous rotation must never replay a used refresh
            generation to old
        }
        val body = JSONObject().put("refresh_token", previous).toString().toRequestBody("application/json".toMediaType())
        val call=make("/api/v1/auth/token", "POST", body)
        try { call.execute().use { install(JSONObject(read(it).toString(Charsets.UTF_8)), expected) } }
        catch (error: java.io.IOException) {
            synchronized(credentialState) {
                if (call.request().tag(SendTrace::class.java)?.sent?.get()==false && expected==generation) vault.put(endpoint.origin, previous)
            }
            throw error
        }
        access
    }
    suspend fun health(): Boolean = withContext(Dispatchers.IO) {
        make("/health", "GET", null).execute().use { JSONObject(read(it).toString(Charsets.UTF_8)).optString("service") == "jarvis-server" }
    }
    fun hasCredential() = vault.get(endpoint.origin) != null
    suspend fun json(path: String, method: String = "GET", body: JSONObject? = null, authenticated: Boolean = true): JSONObject = withContext(Dispatchers.IO) {
        val data = if (method in setOf("POST", "PUT", "PATCH")) (body ?: JSONObject()).toString().toRequestBody("application/json".toMediaType()) else null
        make(path, method, data, if (authenticated) bearer() else null).execute().use { JSONObject(read(it).toString(Charsets.UTF_8)) }
    }
    suspend fun finishPair(body: JSONObject) = withContext(Dispatchers.IO) {
        val expected = generation
        rotation.withLock { val result=json("/api/v1/pairing/token", "POST", body, false); coroutineContext.ensureActive(); install(result, expected) }
    }
    suspend fun stream(body: JSONObject, event: suspend (JSONObject) -> Unit) = withContext(Dispatchers.IO) {
        val call = make("/api/v1/chat/stream", "POST", body.toString().toRequestBody("application/json".toMediaType()), bearer())
        streamCall = call
        try { call.execute().use { response ->
            if (!response.isSuccessful) error(response)
            val source = response.body!!.source(); var total = 0; var done = false
            while (!source.exhausted()) {
                coroutineContext.ensureActive()
                val line = source.readUtf8LineStrict(200_000)
                total += line.length; require(total < 1_000_000)
                if (line.startsWith("data:")) {
                    val data = JSONObject(line.removePrefix("data:").trim())
                    event(data); if (data.optString("type") == "done") { done = true; break }
                }
            }
            if (!done) throw MobileError("stream_lost", message="Antwoord onderbroken; je vraag wordt niet automatisch opnieuw verstuurd")
        } } finally { streamCall = null }
    }
    suspend fun transcribe(wav: ByteArray,speculative:Boolean=false): String = withContext(Dispatchers.IO) {
        val call = make("/api/v1/mobile/speech/transcribe", "POST", wav.toRequestBody("audio/wav".toMediaType()), bearer()); transcriptionCall = call
        if(speculative)call.timeout().timeout(8,TimeUnit.SECONDS)
        try { call.execute().use { JSONObject(read(it).toString(Charsets.UTF_8)).getString("text") } } finally { if(transcriptionCall===call)transcriptionCall = null }
    }
    suspend fun previewVoice(body:JSONObject):JSONObject=withContext(Dispatchers.IO) {
        val call=make("/api/v1/natural/voice-studio/preview","POST",body.toString().toRequestBody("application/json".toMediaType()),bearer());synthesisCall=call
        try {call.execute().use {JSONObject(read(it,8_000_000).toString(Charsets.UTF_8))}}finally{if(synthesisCall===call)synthesisCall=null}
    }
    suspend fun synthesize(text: String, speed: Float,utterance: String?=null,conversation:String?=null): ByteArray = withContext(Dispatchers.IO) {
        val body = JSONObject().put("text", text)
        if(utterance==null)body.put("speed",speed) else body.put("utterance_id",utterance)
        conversation?.let {body.put("conversation_id",it)}
        val call = make("/api/v1/mobile/speech/synthesize", "POST", body.toString().toRequestBody("application/json".toMediaType()), bearer()); synthesisCall = call
        try { call.execute().use { read(it, 8_000_000) } } finally { if(synthesisCall===call)synthesisCall = null }
    }
    fun cancelTranscription() {transcriptionCall?.cancel()}
    fun stop() { streamCall?.cancel(); transcriptionCall?.cancel();synthesisCall?.cancel() }
    fun invalidatePendingAuth() = synchronized(credentialState) { generation++ }
    fun forget() {
        synchronized(credentialState) { generation++; access = ""; vault.drop(endpoint.origin) }
        stop()
    }
}
