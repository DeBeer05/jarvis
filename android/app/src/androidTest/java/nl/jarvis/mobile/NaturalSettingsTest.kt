package nl.jarvis.mobile

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.lifecycle.ViewModelStore
import androidx.test.platform.app.InstrumentationRegistry
import nl.jarvis.mobile.core.Connection
import nl.jarvis.mobile.features.JarvisViewModel
import nl.jarvis.mobile.features.ScreenState
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.After
import org.junit.Rule
import org.junit.Test

class NaturalSettingsTest {
    @get:Rule val compose=createComposeRule()
    private val store=ViewModelStore()
    private fun fixture(): JSONObject = InstrumentationRegistry.getInstrumentation().context.assets.open("natural-settings-contract.json").use {JSONObject(it.bufferedReader().readText())}
    @After fun cleanup() {compose.runOnIdle {store.clear()}}

    @Test fun completeContractRoundtripsNumbersWithoutChangingPrivileges() {
        val fixture=fixture();val schema=fixture.getJSONObject("schema");val original=fixture.getJSONObject("document").getJSONObject("settings")
        val draft=JSONObject(original.toString());draft.getJSONObject("ai").put("temperature","0.4");draft.getJSONObject("personality").put("humor","80")
        val validated=SettingsDraft.validated(draft.toString(),schema)
        assertEquals(.4,validated.getJSONObject("ai").getDouble("temperature"),.0001)
        assertEquals(80,validated.getJSONObject("personality").getInt("humor"))
        assertEquals(SettingsDraft.canonical(original.getJSONObject("autonomy")),SettingsDraft.canonical(validated.getJSONObject("autonomy")))
        draft.getJSONObject("ai").put("temperature","not-a-number")
        assertThrows(Exception::class.java) {SettingsDraft.validated(draft.toString(),schema)}
        assertEquals(14,schema.getJSONObject("categories").length())
    }

    @Test fun nativeSettingsRenderTypedFieldsAndKeepUnsavedInputUntilCancel() {
        val data=fixture();val context=InstrumentationRegistry.getInstrumentation().targetContext.applicationContext as JarvisApplication
        lateinit var model: JarvisViewModel
        compose.runOnUiThread {model=JarvisViewModel(context);store.put("synthetic-settings",model)}
        val state=ScreenState(connection=Connection(online=true,authenticated=true),naturalSettings=data.getJSONObject("document").toString(),naturalSchema=data.getJSONObject("schema").toString())
        compose.setContent {JarvisTheme("dark") {Column(Modifier.verticalScroll(rememberScrollState())) {NaturalSettingsScreen(state,model)}}}
        compose.onNodeWithTag("natural-address_name").performScrollTo().performTextInput("Synthetisch")
        compose.onNodeWithText("Niet-opgeslagen wijzigingen").assertExists()
        compose.onNodeWithText("Annuleren",useUnmergedTree=true).performScrollTo().performClick()
        compose.onNodeWithTag("natural-address_name").performScrollTo().assert(SemanticsMatcher.expectValue(SemanticsProperties.EditableText,AnnotatedString("")))
        compose.onNodeWithText("Niet-opgeslagen wijzigingen").assertDoesNotExist()
    }

    @Test fun contactsRenderSearchAndEditorWithoutChangingApprovals() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext.applicationContext as JarvisApplication
        lateinit var model:JarvisViewModel
        compose.runOnUiThread {model=JarvisViewModel(context);store.put("synthetic-contacts",model)}
        val contacts="""{"items":[{"id":"synthetic","name":"Noah Test","email":"noah@example.invalid","aliases":["Collega"],"revision":1}]}"""
        val state=ScreenState(connection=Connection(online=true,authenticated=true),naturalContacts=contacts)
        compose.setContent {JarvisTheme("dark") {Column {NaturalSettingsScreen(state,model)}}}
        compose.onNodeWithText("Adresboek").performClick()
        compose.onNodeWithText("noah@example.invalid").assertExists()
        compose.onNodeWithText("Zoek naam, alias of e-mailadres").performTextInput("collega")
        compose.onNodeWithText("noah@example.invalid").assertExists()
        compose.onNodeWithText("Toevoegen").performClick()
        compose.onNodeWithText("Contact toevoegen").assertExists()
        compose.onNodeWithText("E-mailadres").assertExists()
        compose.onNodeWithText("Annuleren").performClick()
        compose.onNodeWithText("Contact toevoegen").assertDoesNotExist()
    }


    @Test fun voiceStudioShowsInstalledVoicesAndTypedPreviewWithoutRecording() {
        val data=fixture();val context=InstrumentationRegistry.getInstrumentation().targetContext.applicationContext as JarvisApplication
        lateinit var model:JarvisViewModel
        compose.runOnUiThread {model=JarvisViewModel(context);store.put("synthetic-studio",model)}
        val catalogue="""{"providers":[{"id":"supertonic","voices":[{"id":"M1","available":true},{"id":"M2","available":false}]}]}"""
        val state=ScreenState(connection=Connection(online=true,authenticated=true),naturalSettings=data.getJSONObject("document").toString(),voiceStudio=catalogue)
        compose.setContent {JarvisTheme("dark") {Column {NaturalSettingsScreen(state,model)}}}
        compose.onNodeWithText("Voice Studio").performClick()
        compose.onNodeWithText("supertonic · M1").assertExists()
        compose.onNodeWithText("supertonic · M2").assertDoesNotExist()
        compose.onNodeWithText("Beluisteren").assertExists()
        compose.onNodeWithText("Voorbeeldtekst, maximaal 350 tekens").assertExists()
    }

}
