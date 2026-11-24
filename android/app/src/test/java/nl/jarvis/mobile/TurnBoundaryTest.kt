package nl.jarvis.mobile

import nl.jarvis.mobile.voice.TurnBoundary
import org.junit.Assert.*
import org.junit.Test

class TurnBoundaryTest {
    @Test fun incompleteTurnsWaitButCompleteQuestionsFinish() {
        assertFalse(TurnBoundary.complete("Maak vrijdag een afspraak, ehm"))
        assertFalse(TurnBoundary.complete("Maak vrijdag een afspraak"))
        assertFalse(TurnBoundary.complete("Vertel me over mijn"))
        assertTrue(TurnBoundary.complete("Hoe heet je?"))
        assertTrue(TurnBoundary.complete("Maak vrijdag om half vier een afspraak"))
    }
}
