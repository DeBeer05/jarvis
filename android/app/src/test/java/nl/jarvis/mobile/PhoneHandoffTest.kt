package nl.jarvis.mobile

import nl.jarvis.mobile.device.PhoneHandoff
import org.junit.Assert.*
import org.junit.Test

class PhoneHandoffTest {
    @Test fun platformUrisEscapeExternalTextAndDoNotAutoSend() {
        assertEquals("tel:+31612345678",PhoneHandoff.uri("dial","+31612345678"))
        assertEquals("smsto:+31612345678",PhoneHandoff.uri("sms","+31612345678","synthetic"))
        assertTrue(PhoneHandoff.uri("navigate","Utrecht & omgeving").endsWith("q=Utrecht%20%26%20omgeving"))
        assertTrue(PhoneHandoff.uri("whatsapp","+31612345678","a & b").contains("text=a%20%26%20b"))
    }
    @Test fun unsupportedActionsAndInjectedRecipientsAreRejected() {
        for(action in listOf("shell","call","send","intent")) {
            try {PhoneHandoff.uri(action,"test");fail("Unsupported action")}catch(_:IllegalStateException){}
        }
        try {PhoneHandoff.uri("dial","123;123");fail("Invalid phone")}catch(_:IllegalArgumentException){}
        try {PhoneHandoff.uri("email","test@example.invalid","","subject\r\nBcc:other");fail("Header injection")}catch(_:IllegalArgumentException){}
    }
}
