package nl.jarvis.mobile

import android.app.Application
import android.content.Context
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.first
import nl.jarvis.mobile.core.Endpoint
import nl.jarvis.mobile.data.*
import nl.jarvis.mobile.notifications.Notifications
import java.util.concurrent.ConcurrentHashMap

class AppGraph(context: Context) {
    private val progressDirectory=java.io.File(context.cacheDir,"progress-audio")
    val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    val settings = SettingsStore(context)
    val vault = SecretVault(context)
    val cache = ConversationCache(context, vault)
    val notifications = Notifications(context)
    private val clients = ConcurrentHashMap<String, JarvisApi>()
    fun api(origin: String): JarvisApi = clients.computeIfAbsent(origin) { JarvisApi(Endpoint.parse(it, BuildConfig.DEBUG), vault,progressDirectory) }
}
class JarvisApplication: Application() {
    lateinit var graph: AppGraph
        private set
    override fun onCreate() { super.onCreate(); graph = AppGraph(this); graph.notifications.channels()
        graph.scope.launch {nl.jarvis.mobile.notifications.BackgroundSync.configure(this@JarvisApplication,graph.settings.values.first().backgroundSync)}
    }
}
