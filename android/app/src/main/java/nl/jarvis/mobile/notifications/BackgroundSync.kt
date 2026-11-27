package nl.jarvis.mobile.notifications

import android.content.Context
import androidx.work.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.first
import nl.jarvis.mobile.JarvisApplication
import java.util.concurrent.TimeUnit

/** OS-managed best-effort sync, no permanent service, microphone, model or LLM. */
object BackgroundSync {
    fun configure(context:Context,enabled:Boolean) {
        val manager=WorkManager.getInstance(context)
        if(!enabled) {manager.cancelUniqueWork("jarvis-personal-sync");return}
        val request=PeriodicWorkRequestBuilder<PersonalSyncWorker>(15,TimeUnit.MINUTES)
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).setRequiresBatteryNotLow(true).build())
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL,30,TimeUnit.SECONDS).build()
        manager.enqueueUniquePeriodicWork("jarvis-personal-sync",ExistingPeriodicWorkPolicy.KEEP,request)
    }
}

class PersonalSyncWorker(context:Context,parameters:WorkerParameters):CoroutineWorker(context,parameters) {
    override suspend fun doWork():Result {
        val graph=(applicationContext as JarvisApplication).graph
        val settings=graph.settings.values.first()
        if(!settings.backgroundSync)return Result.success()
        val api=graph.api(settings.origin)
        if(!api.hasCredential())return Result.success()
        return try {
            val consent=api.json("/api/v1/natural/device-settings").getJSONObject("settings")
            try {nl.jarvis.mobile.device.DeviceSnapshot.send(applicationContext,api,consent)}catch(cancel:CancellationException){throw cancel}catch(_:Exception){ /* Optional metadata must not block briefings. */ }
            if(!graph.notifications.canShow("important") || "important" !in settings.categories)return Result.success()
            val events=api.json("/api/v1/natural/events").getJSONArray("items")
            for(index in 0 until events.length()) {
                val id=events.getJSONObject(index).getString("id")
                if(graph.settings.personalEventSeen(api.endpoint.origin,id) || graph.settings.personalEventSeen(api.endpoint.origin,id,true))continue
                // Persist only the opaque receipt before posting. Keep the server
                // event unread so opening JARVIS can show its actual contents.
                graph.settings.markPersonalEventSeen(api.endpoint.origin,id,true)
                graph.notifications.show("important","Chat")
            }
            Result.success()
        } catch(cancel:CancellationException){throw cancel}
        catch(_:Exception){if(runAttemptCount<3)Result.retry() else Result.failure()}
    }
}
