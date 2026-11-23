package nl.jarvis.mobile

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import org.junit.Rule
import org.junit.Test

class InterfaceTest {
    @get:Rule val compose=createAndroidComposeRule<MainActivity>()
    @Test fun nativeScreensRenderAndNavigationSurvivesStop() {
        compose.onNodeWithText("☰").performClick()
        compose.onNodeWithText("Welkom").performClick()
        compose.onNodeWithText("JARVIS · Welkom").assertIsDisplayed()
        compose.onNodeWithText("☰").performClick()
        compose.onNodeWithText("Spraak").performClick()
        compose.onNodeWithText("Microfoon uit").assertIsDisplayed()
        compose.onNodeWithText("Stop alles").performClick()
        compose.onNodeWithText("Gestopt").assertIsDisplayed()
        compose.onNodeWithText("☰").performClick()
        compose.onNodeWithText("Automatiseringen").performClick()
        compose.onNodeWithText("Zelfstandig binnen regels").assertIsDisplayed()
    }
}
