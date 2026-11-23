package nl.jarvis.mobile

import android.Manifest
import android.app.NotificationManager
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.first
import nl.jarvis.mobile.core.*
import nl.jarvis.mobile.data.*
import nl.jarvis.mobile.notifications.Notifications
import nl.jarvis.mobile.voice.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.Before
import org.junit.After
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class DeviceIntegrationTest {
    private val context=InstrumentationRegistry.getInstrumentation().targetContext
    @Before fun isolateCredentials() { SecretVault(context).drop("http://127.0.0.1:8765") }
    @After fun clearCredentials() { SecretVault(context).drop("http://127.0.0.1:8765") }
    private fun api()=JarvisApi(Endpoint.parse("http://127.0.0.1:8765",true),SecretVault(context))
    private suspend fun pair(api: JarvisApi) {
        val verifier=Proof.verifier()
        val pair=api.json("/api/v1/auth/android-login","POST",JSONObject().put("username","owner").put("password","synthetic-owner-passphrase").put("device_name","Android instrumentation").put("code_challenge",Proof.challenge(verifier)),false)
        assertFalse(pair.has("access_token"))
        val approve=JSONObject().put("request_id",pair.getString("request_id")).put("user_code",pair.getString("user_code"))
        OkHttpClient().newCall(Request.Builder().url("http://127.0.0.1:8765/api/test/approve").post(approve.toString().toRequestBody("application/json".toMediaType())).build()).execute().use {assertTrue(it.isSuccessful)}
        api.finishPair(JSONObject().put("grant_type","urn:ietf:params:oauth:grant-type:device_code").put("device_code",pair.getString("device_code")).put("code_verifier",verifier))
    }
    @Test fun keystoreAndSettingsPersistWithoutPlaintext() = runBlocking {
        val vault=SecretVault(context); val origin="synthetic:"+UUID.randomUUID();val value=Proof.verifier()
        vault.put(origin,value);assertEquals(value,SecretVault(context).get(origin))
        assertFalse(context.getSharedPreferences("sealed_credentials",0).all.values.any {it.toString().contains(value)})
        assertThrows(Exception::class.java){vault.open(vault.seal("cache","one"),"another")}
        vault.drop(origin);assertNull(vault.get(origin))
        val store=SettingsStore(context);val original=store.values.first()
        store.save(original.copy(speed=1.2f));assertEquals(1.2f,SettingsStore(context).values.first().speed)
        store.save(original)
        val cache=ConversationCache(context,vault);cache.put(origin,"example","Private synthetic text")
        assertEquals("Private synthetic text",cache.get(origin,"example"));cache.clear(origin)
        cache.put(origin,"late","Should never be stored") {false}
        assertNull(cache.get(origin,"late"))
    }
    @Test fun realTcpPairRefreshChatHistoryPushAndRevocation() = runBlocking {
        val api=api();assertTrue(api.health());pair(api)
        assertEquals("android",api.json("/api/v1/auth/device").getString("type"))
        var conversation="";var deltas=0
        api.stream(JSONObject().put("message","Mijn naam is Eva").put("provider","ollama").put("request_id",UUID.randomUUID().toString())) {event ->
            if(event.optString("type")=="meta")conversation=event.getString("conversation_id")
            if(event.optString("type")=="delta")deltas++
        }
        assertTrue(conversation.isNotBlank() && deltas>0)
        api.stream(JSONObject().put("message","Hoe heet ik?").put("conversation_id",conversation).put("provider","ollama").put("request_id",UUID.randomUUID().toString())) {}
        assertEquals(2,api.json("/api/v1/chat/conversations/$conversation").getJSONArray("turns").length())
        assertTrue(api.json("/api/v1/chat/conversations?limit=100&offset=0").getJSONArray("items").length()>0)
        val restored=api();assertTrue(restored.hasCredential());assertTrue(restored.json("/api/v1/auth/session").has("device_id"))
        val push=restored.json("/api/v1/mobile/push","POST",JSONObject().put("token","synthetic-fcm-registration-token"))
        assertFalse(push.getBoolean("external_delivery_available"))
        restored.json("/api/v1/mobile/push","DELETE")
        restored.json("/api/v1/chat/conversations/$conversation","DELETE")
        restored.json("/api/v1/auth/disconnect","POST");restored.forget()
        assertThrows(MobileError::class.java) {runBlocking {api.json("/api/v1/auth/session")}}
        api.forget()
    }
    @Test fun realPiperWhisperAndAndroidAudioInterfaces() = runBlocking {
        val api=api();pair(api)
        val wav=api.synthesize("Hallo, ik ben Jarvis. Hoe kan ik je vandaag helpen?",1f)
        val (rate,pcm)=Wav.decode(wav);assertTrue(rate>0 && pcm.any {it.toInt()!=0})
        // STT accepts bounded PCM16 at 16 kHz. Resample the real Piper response.
        val count=pcm.size/2;val samples=java.nio.ByteBuffer.wrap(pcm).order(java.nio.ByteOrder.LITTLE_ENDIAN).asShortBuffer()
        val target=java.nio.ByteBuffer.allocate((count.toLong()*16000/rate).toInt()*2).order(java.nio.ByteOrder.LITTLE_ENDIAN)
        repeat(target.capacity()/2){i -> target.putShort(samples.get((i.toLong()*rate/16000).toInt().coerceAtMost(count-1)))}
        val text=api.transcribe(Wav.encode(target.array()))
        assertTrue(text.lowercase().contains("hallo"))
        val audio=AudioClient(context)
        audio.play(wav,0) // Actual Android AudioTrack, not a mocked output.
        val playback=launch {audio.play(wav,0)};delay(200);audio.stop();withTimeout(1500){playback.join()}
        InstrumentationRegistry.getInstrumentation().uiAutomation.grantRuntimePermission(context.packageName,Manifest.permission.RECORD_AUDIO)
        val capture=async {audio.record(0){}}
        delay(500);audio.finishRecording();withTimeout(2000){capture.await()}
        // Emulator host audio is disabled: capture tests driver lifecycle, not user's voice.
        api.json("/api/v1/auth/disconnect","POST");api.forget()
    }
    @Test fun notificationChannelsAreRealAndPrivate() {
        Notifications(context).channels()
        val manager=context.getSystemService(NotificationManager::class.java)
        listOf("urgent","appointments","important","news").forEach {assertNotNull(manager.getNotificationChannel(it))}
        assertNotEquals(android.app.Notification.VISIBILITY_PUBLIC,manager.getNotificationChannel("urgent").lockscreenVisibility)
    }
    @Test fun untrustedTlsAndOtherOriginsNeverReceiveCredentials() = runBlocking {
        val certificate=okhttp3.tls.HeldCertificate.Builder().commonName("localhost").addSubjectAlternativeName("localhost").build()
        val server=mockwebserver3.MockWebServer()
        server.useHttps(okhttp3.tls.HandshakeCertificates.Builder().heldCertificate(certificate).build().sslSocketFactory())
        server.start()
        try {
            val vault=SecretVault(context)
            val endpoint=Endpoint.parse("https://localhost:${server.port}",false)
            assertFalse(JarvisApi(endpoint,vault).hasCredential())
            assertThrows(javax.net.ssl.SSLHandshakeException::class.java){runBlocking{JarvisApi(endpoint,vault).health()}}
        } finally {server.close()}
        Unit
    }
}
