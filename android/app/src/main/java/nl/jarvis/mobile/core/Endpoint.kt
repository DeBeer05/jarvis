package nl.jarvis.mobile.core

import java.net.URI
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64

data class Endpoint(val origin: String) {
    companion object {
        fun parse(value: String, debug: Boolean): Endpoint {
            val uri = try { URI(value.trim()) } catch (_: Exception) { throw IllegalArgumentException("Ongeldig serveradres") }
            require(uri.host != null && uri.userInfo == null && uri.rawQuery == null && uri.rawFragment == null && uri.rawPath in listOf("", "/")) { "Gebruik alleen een serveradres, zonder pad of inloggegevens" }
            require(uri.scheme == "https" || (debug && uri.scheme == "http" && uri.host in setOf("127.0.0.1", "localhost", "10.0.2.2"))) { "HTTPS is verplicht; lokale HTTP werkt alleen in de debug-app" }
            require(uri.port == -1 || uri.port in 1..65535) { "Ongeldige poort" }
            return Endpoint(value.trim().trimEnd('/'))
        }
    }
}
object Proof {
    fun verifier(): String = Base64.getUrlEncoder().withoutPadding().encodeToString(ByteArray(32).also { SecureRandom().nextBytes(it) })
    fun challenge(value: String): String = Base64.getUrlEncoder().withoutPadding().encodeToString(MessageDigest.getInstance("SHA-256").digest(value.toByteArray(Charsets.US_ASCII)))
    fun key(value: String): String = MessageDigest.getInstance("SHA-256").digest(value.toByteArray()).joinToString("") { "%02x".format(it) }
}
class MobileError(val code: String, val status: Int = 0, message: String): Exception(message)

class SentenceBuffer {
    private var text = ""
    fun add(delta: String, final: Boolean = false): List<String> {
        text += delta
        require(text.length <= 18000)
        val result = mutableListOf<String>()
        while (text.isNotEmpty()) {
            val end = Regex("[.!?][\\\"')]*\\s|\\n").find(text)?.range?.last?.plus(1)
                ?: if (text.length > 400) text.lastIndexOf(' ', 399).takeIf { it > 0 } else null
            val length = end ?: if (final) text.length else break
            result += text.take(length).trim().replace(Regex("[`*_#]"), "")
            text = text.drop(length)
        }
        return result.filter { it.isNotBlank() }
    }
}
