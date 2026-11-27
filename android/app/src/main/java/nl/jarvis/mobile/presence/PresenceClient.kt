package nl.jarvis.mobile.presence

import android.app.KeyguardManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.PowerManager
import android.os.SystemClock
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import nl.jarvis.mobile.data.JarvisApi
import nl.jarvis.mobile.data.SettingsStore
import org.json.JSONObject

/** Foreground-only, opt-in status. No app usage, screen content or key logging. */
class PresenceClient(
    private val context:Context,
    private val store:SettingsStore,
    private val api:()->JarvisApi?,
    private val authenticated:()->Boolean,
    private val privateMode:()->Boolean,
    private val state:(JSONObject?,String)->Unit,
    private val event:(String)->Unit,
    private val handoff:(JSONObject?)->Unit={},
    private val stop:()->Unit={}
) {
    private val mutex=Mutex()
    private var job:Job?=null
    private var scope:CoroutineScope?=null
    private var receiver:BroadcastReceiver?=null
    private var document:JSONObject?=null
    private var lastApi:JarvisApi?=null
    private var lastGeneration=-1
    private var sequence:Int?=null
    private var lastInput=SystemClock.elapsedRealtime()
    private var foreground=false
    val enabled:Boolean get()=document?.optJSONObject("settings")?.optBoolean("presence_allowed")==true

    fun install(value:JSONObject) {
        document=value
        if(!enabled || privateMode()) unregister() else register()
        if(value.optJSONObject("settings")?.optBoolean("handoff_allowed")!=true || privateMode())handoff(null)
        state(value,if(enabled) "Aanwezigheid delen toegestaan; alleen zolang JARVIS actief is" else "Aanwezigheid delen uitgeschakeld")
    }
    fun interaction() {if(enabled) lastInput=SystemClock.elapsedRealtime()}
    fun start(scope:CoroutineScope) {
        this.scope=scope;foreground=true;lastInput=SystemClock.elapsedRealtime()
        if(job?.isActive==true)return
        job=scope.launch {while(isActive) {step();delay(20000)}}
    }
    fun stop() {foreground=false;job?.cancel();job=null;unregister()}
    fun clear() {stop();document=null;lastApi=null;sequence=null;handoff(null);state(null,"Aanwezigheid niet gekoppeld")}
    fun kick() {scope?.launch {step()}}
    private fun register() {
        if(!foreground || receiver!=null || !enabled || privateMode())return
        val value=object:BroadcastReceiver() {override fun onReceive(context:Context?,intent:Intent?) {kick()}}
        ContextCompat.registerReceiver(context,value,IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_OFF);addAction(Intent.ACTION_SCREEN_ON);addAction(Intent.ACTION_USER_PRESENT)
        },ContextCompat.RECEIVER_NOT_EXPORTED)
        receiver=value
    }
    private fun unregister() {receiver?.let {runCatching {context.unregisterReceiver(it)}};receiver=null}
    private suspend fun step() {
        if(!foreground || !authenticated() || !mutex.tryLock())return
        try {
            val current=api() ?: return
            if(current!==lastApi || current.generation!=lastGeneration) {
                unregister();document=null;sequence=null;lastApi=current;lastGeneration=current.generation
            }
            if(document==null)install(current.json("/api/v1/natural/device-settings"))
            if(sequence==null)sequence=current.json("/api/v1/natural/presence").optInt("sequence",0)
            if(!foreground || current!==api() || !authenticated())return
            val locked=context.getSystemService(KeyguardManager::class.java).isDeviceLocked || !context.getSystemService(PowerManager::class.java).isInteractive
            if(privateMode())unregister()
            if(enabled && !privateMode()) {
                register()
                val next=(sequence ?: 0)+1
                val sample=JSONObject().put("sequence",next).put("locked",locked)
                    .put("idle_seconds",((SystemClock.elapsedRealtime()-lastInput)/1000).coerceIn(0,86400)).put("hint","normal")
                val result=current.json("/api/v1/natural/presence/signals","POST",sample)
                sequence=result.getInt("sequence")
                state(document,"Modus: ${result.optString("label","Onbekend")}")
            }
            if(!locked && foreground && current===api() && authenticated()) {
                if(!privateMode())document?.optJSONObject("settings")?.let {
                    try {nl.jarvis.mobile.device.DeviceSnapshot.send(context,current,it)}catch(cancel:CancellationException){throw cancel}catch(_:Exception){ /* Optional metadata must not block the inbox. */ }
                }
                if(document?.optJSONObject("settings")?.optBoolean("handoff_allowed")==true && !privateMode()) {
                    val actions=current.json("/api/v1/natural/mobile-handoffs").getJSONArray("items")
                    var first:JSONObject?=null
                    for(index in 0 until actions.length()) {
                        val item=actions.getJSONObject(index)
                        if(!store.personalEventSeen(current.endpoint.origin,item.getString("id"))) {first=item;break}
                    }
                    if(foreground && current===api() && authenticated())handoff(first)
                }
                val items=current.json("/api/v1/natural/events").getJSONArray("items")
                for(index in 0 until items.length()) {
                    if(!foreground || current!==api() || !authenticated())return
                    val item=items.getJSONObject(index);val id=item.getString("id")
                    if(!store.personalEventSeen(current.endpoint.origin,id)) {
                        store.markPersonalEventSeen(current.endpoint.origin,id)
                        if(!foreground || current!==api())return
                        val text=item.optJSONObject("payload")?.optString("text") ?: ""
                        if(item.optString("kind")=="control.stop")stop()
                        if(text.isNotBlank())event(text)
                    }
                    current.json("/api/v1/natural/events/$id/ack","POST",JSONObject())
                }
            }
        } catch(cancel:CancellationException) {throw cancel}
        catch(_:Exception) {unregister();document=null;sequence=null;state(null,"Aanwezigheid tijdelijk niet beschikbaar; gesprek blijft werken")}
        finally {mutex.unlock()}
    }
}
