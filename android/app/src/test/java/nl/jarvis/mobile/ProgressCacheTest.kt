package nl.jarvis.mobile

import nl.jarvis.mobile.voice.ProgressCache
import nl.jarvis.mobile.voice.ProgressClip
import java.nio.file.Files
import java.security.MessageDigest
import org.junit.Assert.*
import org.junit.Test

class ProgressCacheTest {
    @Test fun verifiesVoiceAndChecksumBeforeReusingAudio() {
        val root=Files.createTempDirectory("jarvis-progress").toFile()
        try {
            val cache=ProgressCache(root);val raw=ByteArray(100)
            val checksum=MessageDigest.getInstance("SHA-256").digest(raw).joinToString(""){"%02x".format(it)}
            val clip=ProgressClip("general-00","f".repeat(32),checksum,"Een ogenblik.")
            assertNull(cache.get("https://example.test",clip));cache.put("https://example.test",clip,raw)
            assertArrayEquals(raw,cache.get("https://example.test",clip))
            assertNull(cache.get("https://example.test",clip.copy(voiceKey="b".repeat(32))))
        }finally{root.deleteRecursively()}
    }
}
