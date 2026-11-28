package nl.jarvis.mobile.device

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import nl.jarvis.mobile.JarvisApplication
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicBoolean

/** Counts only. Never reads Notification.extras, titles, messages or action buttons. */
class JarvisNotificationListener:NotificationListenerService() {
    private val pending=AtomicBoolean(false)
    companion object {
        @Volatile private var connected:JarvisNotificationListener?=null
        fun counts(allowed:Set<String>):JSONArray? {
            val listener=connected ?: return null
            return runCatching {
                val counts=listener.activeNotifications.filter{it.packageName in allowed}.groupingBy{it.packageName}.eachCount()
                JSONArray().apply {counts.entries.take(20).forEach {(name,count)->put(JSONObject().put("package",name).put("count",count.coerceAtMost(1000)))}}
            }.getOrNull()
        }
    }
    override fun onListenerConnected() {connected=this;schedule()}
    override fun onListenerDisconnected() {if(connected===this)connected=null}
    override fun onDestroy() {if(connected===this)connected=null;super.onDestroy()}
    override fun onNotificationPosted(notification:StatusBarNotification?) {schedule()}
    override fun onNotificationRemoved(notification:StatusBarNotification?) {schedule()}
    private fun schedule() {
        if(!pending.compareAndSet(false,true))return
        val graph=(application as JarvisApplication).graph
        graph.scope.launch {
            try {
                delay(10000) // Coalesce bursts. No per-notification provider/model calls.
                if(connected!==this@JarvisNotificationListener)return@launch
                val settings=graph.settings.values.first();val api=graph.api(settings.origin)
                if(!api.hasCredential())return@launch
                val consent=api.json("/api/v1/natural/device-settings").getJSONObject("settings")
                if(consent.optBoolean("notification_allowed"))DeviceSnapshot.send(this@JarvisNotificationListener,api,consent)
            }catch(_:Exception){ /* OS still owns the notifications; retry on the next change/sync. */ }
            finally {pending.set(false)}
        }
    }
}
