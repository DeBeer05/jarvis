package nl.jarvis.mobile.data

import android.content.Context
import androidx.room.*
import nl.jarvis.mobile.core.Proof
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

@Entity(tableName = "conversation_cache", primaryKeys = ["profile", "id"])
data class CachedConversation(val profile: String, val id: String, val sealed: ByteArray)
@Dao interface CacheDao {
    @Query("SELECT * FROM conversation_cache WHERE profile=:profile AND id=:id") suspend fun get(profile: String, id: String): CachedConversation?
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun put(item: CachedConversation)
    @Query("DELETE FROM conversation_cache WHERE profile=:profile") suspend fun clear(profile: String)
}
@Database(entities = [CachedConversation::class], version = 1, exportSchema = false)
abstract class CacheDatabase: RoomDatabase() { abstract fun cache(): CacheDao }
class ConversationCache(context: Context, private val vault: SecretVault) {
    private val database = Room.databaseBuilder(context, CacheDatabase::class.java, "conversations.db").build()
    private val writes = Mutex()
    suspend fun put(origin: String, id: String, text: String, valid: () -> Boolean = { true }) = writes.withLock {
        if (valid()) database.cache().put(CachedConversation(Proof.key(origin), id, vault.seal(text, "cache:$origin:$id")))
    }
    suspend fun get(origin: String, id: String): String? = try {
        database.cache().get(Proof.key(origin), id)?.let { vault.open(it.sealed, "cache:$origin:$id") }
    } catch (_: Exception) { clear(origin); null }
    suspend fun clear(origin: String) = writes.withLock { database.cache().clear(Proof.key(origin)) }
}
