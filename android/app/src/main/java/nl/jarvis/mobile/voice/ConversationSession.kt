package nl.jarvis.mobile.voice

import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import nl.jarvis.mobile.core.MobileError
import nl.jarvis.mobile.data.JarvisApi
import org.json.JSONObject

data class AudioLease(val conversation: String,val device: String,val epoch: Int,val revision: Int,val state: String) {
    companion object {fun parse(value: JSONObject)=AudioLease(value.getString("conversation_id"),value.getString("device_id"),value.getInt("epoch"),value.getInt("revision"),value.getString("state"))}
}

/** Foreground-only audio ownership. This adapter never executes an automation. */
class ConversationSession(private val scope: CoroutineScope,private val api:()->JarvisApi?,private val foreground:()->Boolean,private val lost:(Throwable)->Unit,private val changed:(AudioLease?)->Unit) {
    private val lock=Mutex();private var heartbeat: Job?=null
    private var session: AudioLease?=null;private var transport: JarvisApi?=null
    private var serial=0
    private suspend fun send(client: JarvisApi,lease: AudioLease,event: String): AudioLease = AudioLease.parse(client.json("/api/v1/natural/conversations/${lease.conversation}/events","POST",JSONObject().put("event",event).put("epoch",lease.epoch)))

    private fun keepAlive() {
        heartbeat?.cancel();heartbeat=scope.launch {
            while(isActive && foreground()) {
                delay(20000)
                try {lock.withLock {
                    val lease=session ?: return@withLock;val client=transport ?: return@withLock
                    if(client!==api() || !foreground())return@withLock
                    session=send(client,lease,"heartbeat");changed(session)
                }} catch(cancel: CancellationException) {throw cancel}
                  catch(error: Exception) {session=null;changed(null);lost(error);return@launch}
            }
        }
    }

    suspend fun prepare(conversation: String?,takeover: Boolean=false): AudioLease = lock.withLock {
        check(foreground()) {"Open de app voordat je praat"}
        val client=api() ?: throw MobileError("offline",message="Server niet beschikbaar")
        val expected=serial
        var lease=session
        if(transport!==client || lease?.conversation!=conversation || takeover)lease=null
        if(lease!=null) {
            val remote=AudioLease.parse(client.json("/api/v1/natural/conversations/${lease.conversation}/state"))
            if(remote.state !in setOf("STANDBY","RECONNECTING","ENDING","ERROR") && (remote.device!=lease.device || remote.epoch!=lease.epoch))throw MobileError("conversation_conflict",409,"Dit gesprek is op een ander apparaat actief. Neem het expliciet over")
            lease=if(remote.state in setOf("STANDBY","RECONNECTING","ENDING","ERROR"))null else remote
        }
        if(lease==null) {
            val body=JSONObject().put("takeover",takeover);conversation?.let {body.put("conversation_id",it)}
            lease=AudioLease.parse(client.json("/api/v1/natural/conversations/start","POST",body))
            lease=send(client,lease,"listening")
        }
        if(lease.state in setOf("PROCESSING","THINKING","ASSISTANT_SPEAKING","EXECUTING_ACTION"))lease=send(client,lease,"interrupted")
        lease=send(client,lease,"processing")
        check(expected==serial && foreground() && api()===client) {"Gespreksactivatie geannuleerd"}
        session=lease;transport=client;changed(lease);keepAlive();lease
    }

    suspend fun listening() = lock.withLock {
        val lease=session ?: return@withLock;val client=transport ?: return@withLock
        if(client===api() && foreground()) {session=send(client,lease,"listening");changed(session)}
    }

    fun end() {
        serial++;heartbeat?.cancel();heartbeat=null
        val previous=session;val client=transport;session=null;transport=null;changed(null)
        if(previous!=null && client!=null)scope.launch {
            try {withTimeout(3000) {send(client,previous,"ending")}}catch(_:Exception) { /* Server lease also expires; never retry an action. */ }
        }
    }

    suspend fun endBeforeText() {
        val previous=session;val client=transport
        serial++;heartbeat?.cancel();heartbeat=null;session=null;transport=null;changed(null)
        if(previous!=null && client!=null) {
            try {send(client,previous,"ending")}catch(cancel:CancellationException){throw cancel}
            catch(_:Exception){throw MobileError("conversation_conflict",409,"De spraaksessie kon niet veilig worden afgesloten. Hervat het gesprek voordat je opnieuw verstuurt")}
        }
    }
}
