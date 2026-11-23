package nl.jarvis.mobile.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import android.util.Base64
import nl.jarvis.mobile.core.Proof

class SecretVault(context: Context) {
    private val preferences = context.getSharedPreferences("sealed_credentials", Context.MODE_PRIVATE)
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("jarvis-v1", null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder("jarvis-v1", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    @Synchronized fun seal(value: String, aad: String): ByteArray {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()); updateAAD(aad.toByteArray()) }
        return cipher.iv + cipher.doFinal(value.toByteArray())
    }
    @Synchronized fun open(value: ByteArray, aad: String): String {
        require(value.size >= 28)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply {
            init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, value.copyOfRange(0, 12))); updateAAD(aad.toByteArray())
        }
        return cipher.doFinal(value.copyOfRange(12, value.size)).toString(Charsets.UTF_8)
    }
    fun get(origin: String): String? = try {
        preferences.getString(Proof.key(origin), null)?.let { open(Base64.decode(it, Base64.NO_WRAP), origin) }
    } catch (_: Exception) { drop(origin); null }
    fun put(origin: String, value: String) {
        check(preferences.edit().putString(Proof.key(origin), Base64.encodeToString(seal(value, origin), Base64.NO_WRAP)).commit()) { "Veilige opslag niet beschikbaar" }
    }
    fun drop(origin: String) { preferences.edit().remove(Proof.key(origin)).commit() }
}
