package nl.jarvis.mobile.data

import android.content.Context
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.first
import nl.jarvis.mobile.BuildConfig

private val Context.settingsData by preferencesDataStore("settings")
data class Preferences(
    val origin: String = if (BuildConfig.DEBUG) "http://127.0.0.1:8765" else "",
    val automatic: Boolean = true, val theme: String = "dark", val language: String = "nl",
    val speed: Float = 1f, val voiceOutput: Boolean = true,
    val categories: Set<String> = setOf("urgent", "appointments", "important", "news"),
    val firebaseEnabled: Boolean = false, val inputDevice: Int = 0, val outputDevice: Int = 0,
    val backgroundSync:Boolean=false
)
class SettingsStore(private val context: Context) {
    private fun receiptKey(origin:String,background:Boolean=false)=stringPreferencesKey((if(background)"background_events_" else "personal_events_")+java.security.MessageDigest.getInstance("SHA-256").digest(origin.toByteArray()).joinToString(""){"%02x".format(it)})
    suspend fun personalEventSeen(origin:String,id:String,background:Boolean=false):Boolean =
        (context.settingsData.data.first()[receiptKey(origin,background)] ?: "").split(',').contains(id)
    suspend fun markPersonalEventSeen(origin:String,id:String,background:Boolean=false) {
        require(runCatching {java.util.UUID.fromString(id)}.isSuccess)
        context.settingsData.edit {p -> val key=receiptKey(origin,background)
            p[key]=((p[key] ?: "").split(',').filter {it.isNotBlank() && it!=id}+id).takeLast(200).joinToString(",")
        }
    }
    private fun cursorKey(origin: String)=doublePreferencesKey("notification_cursor_"+java.security.MessageDigest.getInstance("SHA-256").digest(origin.toByteArray()).joinToString(""){"%02x".format(it)})
    suspend fun notificationCursor(origin: String):Double = context.settingsData.data.first()[cursorKey(origin)] ?: (System.currentTimeMillis()/1000.0)
    suspend fun notificationSeen(origin: String,at: Double) { context.settingsData.edit { p -> val key=cursorKey(origin);p[key]=maxOf(p[key] ?: 0.0,at) } }
    private val origin = stringPreferencesKey("origin")
    val values = context.settingsData.data.map { p -> Preferences(
        p[origin] ?: Preferences().origin, p[booleanPreferencesKey("automatic")] ?: true,
        p[stringPreferencesKey("theme")] ?: "dark", p[stringPreferencesKey("language")] ?: "nl",
        p[floatPreferencesKey("speed")] ?: 1f, p[booleanPreferencesKey("voiceOutput")] ?: true,
        p[stringSetPreferencesKey("categories")] ?: Preferences().categories,
        p[booleanPreferencesKey("firebase")] ?: false, p[intPreferencesKey("input")] ?: 0, p[intPreferencesKey("output")] ?: 0,
        p[booleanPreferencesKey("backgroundSync")] ?: false
    ) }
    suspend fun save(value: Preferences) { context.settingsData.edit { p ->
        p[origin] = value.origin; p[booleanPreferencesKey("automatic")] = value.automatic
        p[stringPreferencesKey("theme")] = value.theme; p[stringPreferencesKey("language")] = value.language
        p[floatPreferencesKey("speed")] = value.speed.coerceIn(.7f, 1.5f)
        p[booleanPreferencesKey("voiceOutput")] = value.voiceOutput
        p[booleanPreferencesKey("backgroundSync")] = value.backgroundSync
        p[stringSetPreferencesKey("categories")] = value.categories
        p[booleanPreferencesKey("firebase")] = value.firebaseEnabled
        p[intPreferencesKey("input")] = value.inputDevice; p[intPreferencesKey("output")] = value.outputDevice
    } }
}
