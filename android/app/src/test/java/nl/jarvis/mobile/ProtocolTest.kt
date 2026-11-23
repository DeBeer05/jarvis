package nl.jarvis.mobile

import nl.jarvis.mobile.core.*
import nl.jarvis.mobile.domain.*
import nl.jarvis.mobile.voice.Wav
import org.junit.Assert.*
import org.junit.Test

class ProtocolTest {
    @Test fun endpointTrustIsExplicit() {
        assertEquals("http://127.0.0.1:8765",Endpoint.parse("http://127.0.0.1:8765/",true).origin)
        assertEquals("https://jarvis.example",Endpoint.parse("https://jarvis.example",false).origin)
        listOf("http://192.168.1.1:8765","http://example.com","https://user:pw@example.com","https://example.com/?token=x","https://example.com/evil").forEach { value ->
            assertThrows(IllegalArgumentException::class.java) { Endpoint.parse(value,true) }
        }
        assertThrows(IllegalArgumentException::class.java) {Endpoint.parse("http://10.0.2.2:8765",false)}
    }
    @Test fun pkceMatchesRfc7636() {
        assertEquals("E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM", Proof.challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"))
        assertEquals(43,Proof.verifier().length)
    }
    @Test fun segmentBufferDoesNotSpeakHalfWordsOrDecimals() {
        val buffer=SentenceBuffer()
        assertTrue(buffer.add("Het is 3.").isEmpty())
        assertEquals(listOf("Het is 3.14 euro."),buffer.add("14 euro. En da"))
        assertEquals(listOf("En daarna."),buffer.add("arna.",true))
    }
    @Test fun wavIsBoundedAndChecked() {
        val pcm=byteArrayOf(1,2,3,4)
        val (rate,result)=Wav.decode(Wav.encode(pcm))
        assertEquals(16000,rate); assertArrayEquals(pcm,result)
        assertThrows(IllegalArgumentException::class.java){Wav.decode(byteArrayOf())}
    }
    @Test fun backoffAndFutureCallsDoNotCreateHiddenActions() {
        assertTrue(ConnectionManager.backoff(100) in 60000..60400)
        assertFalse(FutureCall("example",NotificationCategory.news,CallState.unavailable).canRingAutomatically())
        assertTrue(FutureCall("example",NotificationCategory.urgent,CallState.unavailable).canRingAutomatically())
    }
}
