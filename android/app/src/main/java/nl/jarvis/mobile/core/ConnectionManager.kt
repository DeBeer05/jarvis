package nl.jarvis.mobile.core

import android.content.Context
import android.net.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import nl.jarvis.mobile.data.JarvisApi
import kotlin.random.Random

data class Connection(val online: Boolean = false, val authenticated: Boolean = false, val title: String = "Offline", val permissions: Set<String> = emptySet())
class ConnectionManager(context: Context, private val scope: CoroutineScope, private val api: () -> JarvisApi?) {
    private val state = MutableStateFlow(Connection())
    val values = state.asStateFlow()
    private var loop: Job? = null
    private val network = context.getSystemService(ConnectivityManager::class.java)
    private val callback = object: ConnectivityManager.NetworkCallback() { override fun onAvailable(network: Network) { if (loop?.isActive == true) checkNow() } }
    private var registered = false
    private val checkLock = kotlinx.coroutines.sync.Mutex()
    fun checkNow() { scope.launch { check() } }
    private suspend fun check(): Boolean {
        if (!checkLock.tryLock()) return state.value.online
        try {
            val client = api() ?: return false
            val generation = client.generation
            if (!client.health()) { state.value = Connection(title="Onbekende server"); return false }
            if (!client.hasCredential()) { state.value = Connection(true, false, "Inloggen / koppelen nodig"); return true }
            val session=client.json("/api/v1/auth/session")
            if (api() !== client || !client.hasCredential() || client.generation != generation) return false
            val rights=session.getJSONArray("permissions")
            state.value = Connection(true, true, "Verbonden",(0 until rights.length()).map{rights.getString(it)}.toSet())
            return true
        } catch (error: Exception) {
            if (error is CancellationException) throw error
            val login = error is MobileError && error.status == 401
            state.value = Connection(login, false, if (login) "Opnieuw koppelen nodig" else "Offline · opnieuw verbinden")
            return false
        } finally { checkLock.unlock() }
    }
    fun start(automatic: Boolean) {
        if (loop?.isActive == true) return
        if (!registered) { network.registerDefaultNetworkCallback(callback); registered = true }
        loop = scope.launch {
            var attempt = 0
            do {
                val online = check()
                attempt = if (online) 0 else (attempt + 1).coerceAtMost(6)
                delay(if (online) 20000 else backoff(attempt))
            } while (automatic && isActive)
        }
    }
    fun stop() {
        loop?.cancel(); loop = null
        if (registered) { network.unregisterNetworkCallback(callback); registered = false }
    }
    companion object { fun backoff(attempt: Int): Long = (1000L shl attempt.coerceIn(0, 6)).coerceAtMost(60000) + Random.nextLong(401) }
}
