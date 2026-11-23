package nl.jarvis.mobile.notifications

import android.Manifest
import android.app.*
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.work.*
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import nl.jarvis.mobile.*
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class Notifications(private val context: Context) {
    val categories = listOf("urgent", "appointments", "important", "news")
    fun channels() {
        val manager = context.getSystemService(NotificationManager::class.java)
        categories.forEach { category -> manager.createNotificationChannel(NotificationChannel(category, when(category) {
            "urgent" -> "Urgent"; "appointments" -> "Afspraken"; "important" -> "Belangrijk"; else -> "Nieuws"
        }, if (category == "urgent") NotificationManager.IMPORTANCE_HIGH else NotificationManager.IMPORTANCE_DEFAULT).apply { lockscreenVisibility = Notification.VISIBILITY_PRIVATE }) }
    }
    fun show(category: String) {
        if (category !in categories || (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)) return
        val intent = PendingIntent.getActivity(context, 1, Intent(context, MainActivity::class.java).putExtra("screen", "Meldingen"), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val notification = Notification.Builder(context, category).setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("JARVIS").setContentText("Er staat een melding voor je klaar.")
            .setVisibility(Notification.VISIBILITY_PRIVATE).setAutoCancel(true).setContentIntent(intent).build()
        context.getSystemService(NotificationManager::class.java).notify(category.hashCode(), notification)
    }
    fun enableFirebase(): Boolean {
        if (BuildConfig.FIREBASE_APP_ID.isBlank() || BuildConfig.FIREBASE_API_KEY.isBlank() || BuildConfig.FIREBASE_SENDER_ID.isBlank() || BuildConfig.FIREBASE_PROJECT_ID.isBlank()) return false
        if (FirebaseApp.getApps(context).isEmpty()) FirebaseApp.initializeApp(context, FirebaseOptions.Builder()
            .setApplicationId(BuildConfig.FIREBASE_APP_ID).setApiKey(BuildConfig.FIREBASE_API_KEY)
            .setProjectId(BuildConfig.FIREBASE_PROJECT_ID).setGcmSenderId(BuildConfig.FIREBASE_SENDER_ID).build())
        FirebaseMessaging.getInstance().isAutoInitEnabled = true
        FirebaseMessaging.getInstance().token.addOnSuccessListener { token -> queueToken(context, token) }
        return true
    }
    fun disableFirebase() {
        WorkManager.getInstance(context).cancelUniqueWork("fcm-register")
        (context.applicationContext as JarvisApplication).graph.vault.drop("fcm-pending")
        if (FirebaseApp.getApps(context).isNotEmpty()) {
            FirebaseMessaging.getInstance().isAutoInitEnabled=false
            FirebaseMessaging.getInstance().deleteToken()
        }
    }
    companion object {
        fun queueToken(context: Context, token: String) {
            val graph = (context.applicationContext as JarvisApplication).graph
            graph.vault.put("fcm-pending", token)
            WorkManager.getInstance(context).enqueueUniqueWork("fcm-register", ExistingWorkPolicy.REPLACE,
                OneTimeWorkRequestBuilder<PushRegistrationWorker>().setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                    .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS).build())
        }
    }
}
class JarvisMessagingService: FirebaseMessagingService() {
    override fun onNewToken(token: String) { Notifications.queueToken(this, token) }
    override fun onMessageReceived(message: RemoteMessage) {
        // Never display arbitrary remote title/body, URLs or command payloads.
        val category = message.data["category"] ?: return
        val graph = (application as JarvisApplication).graph
        graph.scope.launch { val settings=graph.settings.values.first(); if (settings.firebaseEnabled && category in settings.categories) graph.notifications.show(category) }
    }
}
class PushRegistrationWorker(context: Context, parameters: WorkerParameters): CoroutineWorker(context, parameters) {
    override suspend fun doWork(): Result {
        val graph = (applicationContext as JarvisApplication).graph
        val settings = graph.settings.values.first()
        if (!settings.firebaseEnabled) { graph.vault.drop("fcm-pending"); return Result.success() }
        val api = graph.api(settings.origin)
        if (!api.hasCredential()) return Result.failure()
        val token = graph.vault.get("fcm-pending") ?: return Result.success()
        return try {
            api.json("/api/v1/mobile/push", "POST", JSONObject().put("token", token).put("categories", JSONArray(settings.categories.toList())))
            graph.vault.drop("fcm-pending"); Result.success()
        } catch (_: Exception) { if (runAttemptCount < 4) Result.retry() else Result.failure() }
    }
}
