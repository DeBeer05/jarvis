package nl.jarvis.mobile

import nl.jarvis.mobile.voice.TurnBoundary
import nl.jarvis.mobile.voice.IncrementalTranscript
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class TurnBoundaryTest {
    @Test fun incrementalAudioUsesBoundedOverlapAndNoRepeatInference() = runBlocking {
        val stream=IncrementalTranscript();val sizes=mutableListOf<Int>()
        val texts=ArrayDeque(listOf("Zet een afspraak met","afspraak met Noah morgen","Noah morgen om twee uur."))
        val recognize:suspend(ByteArray)->String={wav ->sizes.add(wav.size-44);texts.removeFirst()}
        stream.request(ByteArray(256000),recognize)
        stream.request(ByteArray(512000),recognize)
        val final=stream.request(ByteArray(576000),recognize)
        assertEquals("Zet een afspraak met Noah morgen om twee uur.",final)
        assertEquals(listOf(256000,272000,80000),sizes)
        assertEquals(final,stream.request(ByteArray(576000),recognize))
        assertEquals(3,sizes.size)
    }
    @Test fun incompleteTurnsWaitButCompleteQuestionsFinish() {
        assertFalse(TurnBoundary.complete("Maak vrijdag een afspraak, ehm"))
        assertFalse(TurnBoundary.complete("Maak vrijdag een afspraak"))
        assertFalse(TurnBoundary.complete("Vertel me over mijn"))
        assertTrue(TurnBoundary.complete("Hoe heet je?"))
        assertTrue(TurnBoundary.complete("Maak vrijdag om half vier een afspraak"))
    }
}
