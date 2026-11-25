package nl.jarvis.mobile

import nl.jarvis.mobile.voice.EchoGuard
import org.junit.Assert.*
import org.junit.Test

class EchoGuardTest {
    @Test fun ownOutputAndApprovalWordsAreRejected() {
        val spoken="Je hebt morgen een afspraak. Zeg ja om te bevestigen."
        assertTrue(EchoGuard.resemblesOutput("Je hebt morgen een afspraak",spoken))
        assertTrue(EchoGuard.resemblesOutput("JA!",spoken))
        assertTrue(EchoGuard.resemblesOutput("",spoken))
        assertFalse(EchoGuard.resemblesOutput("Wacht even welke afspraak bedoel je?",spoken))
    }
}
