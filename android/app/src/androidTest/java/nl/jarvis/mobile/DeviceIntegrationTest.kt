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
    @Before fun isolateCredentials() {
        SecretVault(context).drop("http://127.0.0.1:8765")
        OkHttpClient().newCall(Request.Builder().url("http://127.0.0.1:8765/api/test/reset-rates").post("{}".toRequestBody("application/json".toMediaType())).build()).execute().use {assertTrue(it.isSuccessful)}
    }
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
    @Test fun automationRightsReminderAndOneUseApproval() = runBlocking {
        val api=api();pair(api)
        try {api.json("/api/v1/automation");fail("Unapproved automation access") }catch(error:MobileError){assertEquals(403,error.status)}
        api.json("/api/test/grant","POST",JSONObject())
        val input=JSONObject().put("text","Synthetic Android reminder").put("at",java.time.OffsetDateTime.now().plusHours(1).toString()).put("repeat","once").put("timezone","Europe/Amsterdam")
        val key=UUID.randomUUID().toString();val body=JSONObject().put("tool","ReminderCreate").put("input",input).put("idempotency_key",key)
        val row=api.json("/api/v1/automation/jobs","POST",body)
        assertEquals(row.getString("id"),api.json("/api/v1/automation/jobs","POST",body).getString("id"))
        assertTrue(api.json("/api/v1/automation").getJSONArray("items").length()>0)
        api.json("/api/v1/automation/jobs/${row.getString("id")}/control","POST",JSONObject().put("status","cancelled"))
        val send=JSONObject().put("draft_id","synthetic").put("message_hash","a".repeat(64)).put("preview","Synthetic message; no actual recipient")
        val proposal=api.json("/api/v1/automation/jobs","POST",JSONObject().put("tool","EmailSend").put("input",send).put("idempotency_key",UUID.randomUUID().toString()))
        val path="/api/v1/automation/jobs/${proposal.getString("id")}";assertEquals("approval",proposal.getString("status"))
        val challenge=api.json("$path/challenge","POST")
        val decision=JSONObject().put("token",challenge.getString("token")).put("approve",false)
        assertEquals("denied",api.json("$path/decision","POST",decision).getString("status"))
        try {api.json("$path/decision","POST",decision);fail("Approval replay") }catch(error:MobileError){assertEquals(400,error.status)}
        api.json("/api/v1/auth/disconnect","POST");api.forget()
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
    @Test fun naturalSettingsMemoryAndExplicitConversationHandoff() = runBlocking {
        val first=api();pair(first)
        val base=first.json("/api/v1/natural/settings")
        val updated=first.json("/api/v1/natural/settings/personality","PATCH",JSONObject().put("revision",base.getInt("revision")).put("changes",JSONObject().put("humor",81)))
        val second=api();pair(second)
        assertEquals(81,second.json("/api/v1/natural/settings").getJSONObject("settings").getJSONObject("personality").getInt("humor"))
        val device=first.json("/api/v1/natural/device-settings");device.getJSONObject("settings").put("input_device",123)
        first.json("/api/v1/natural/device-settings","PUT",JSONObject().put("revision",device.getInt("revision")).put("settings",device.getJSONObject("settings")))
        assertEquals(-1,second.json("/api/v1/natural/device-settings").getJSONObject("settings").getInt("input_device"))
        val memory=first.json("/api/v1/natural/memory","POST",JSONObject().put("category","project").put("content","Android synthetic lantern preference"))
        val found=second.json("/api/v1/natural/memory/search","POST",JSONObject().put("query","lantern"))
        assertEquals(memory.getString("id"),found.getJSONArray("items").getJSONObject(0).getString("id"))
        second.json("/api/v1/natural/memory/${memory.getString("id")}","DELETE")
        assertEquals(0,first.json("/api/v1/natural/memory/search","POST",JSONObject().put("query","lantern")).getJSONArray("items").length())
        val session=first.json("/api/v1/natural/conversations/start","POST",JSONObject())
        val id=session.getString("conversation_id");val epoch=session.getInt("epoch");val events="/api/v1/natural/conversations/$id/events"
        first.json(events,"POST",JSONObject().put("event","listening").put("epoch",epoch))
        first.json(events,"POST",JSONObject().put("event","processing").put("epoch",epoch))
        val input=JSONObject().put("message","Synthetic Android voice turn").put("provider","ollama").put("channel","voice").put("session_epoch",epoch).put("conversation_id",id)
        assertEquals("completed",first.json("/api/v1/chat","POST",input).getString("status"))
        try {second.json("/api/v1/natural/conversations/start","POST",JSONObject().put("conversation_id",id));fail("Silent audio takeover") }catch(error:MobileError){assertEquals(409,error.status)}
        val taken=second.json("/api/v1/natural/conversations/start","POST",JSONObject().put("conversation_id",id).put("takeover",true))
        assertTrue(taken.getInt("epoch")>epoch)
        try {first.json("/api/v1/chat","POST",input);fail("Stale audio accepted") }catch(error:MobileError){assertEquals(409,error.status)}
        assertEquals(1,second.json("/api/v1/chat/conversations/$id").getJSONArray("turns").length())
        second.json(events,"POST",JSONObject().put("event","ending").put("epoch",taken.getInt("epoch")))
        second.json("/api/v1/natural/settings/reset","POST",JSONObject().put("revision",updated.getInt("revision")).put("category","personality"))
        first.json("/api/v1/auth/disconnect","POST");first.forget();second.json("/api/v1/auth/disconnect","POST");second.forget()
    }
    @Test fun oneManualActivationRunsTenSyntheticSpeechTurnsInOneConversation() = runBlocking {
        val api=api();pair(api)
        val application=context.applicationContext as JarvisApplication
        val original=application.graph.settings.values.first()
        val settings=api.json("/api/v1/natural/settings")
        api.json("/api/v1/natural/settings/conversations","PATCH",JSONObject().put("revision",settings.getInt("revision")).put("changes",JSONObject().put("continuous",true)))
        val source=api.synthesize("Ik wil een kort antwoord.",1f)
        val (rate,pcm)=Wav.decode(source);val samples=java.nio.ByteBuffer.wrap(pcm).order(java.nio.ByteOrder.LITTLE_ENDIAN).asShortBuffer()
        val converted=java.nio.ByteBuffer.allocate((samples.limit().toLong()*16000/rate).toInt()*2).order(java.nio.ByteOrder.LITTLE_ENDIAN)
        repeat(converted.capacity()/2) {index->converted.putShort(samples.get((index.toLong()*rate/16000).toInt().coerceAtMost(samples.limit()-1)))}
        val synthetic=Wav.encode(converted.array())
        val recorded=java.util.concurrent.atomic.AtomicInteger();val played=java.util.concurrent.atomic.AtomicInteger()
        val fake=object:AudioClient(context) {
            override suspend fun record(device:Int,threshold:Float,silenceMs:Int,maximumSeconds:Int,echo:Boolean,noise:Boolean,level:(Float)->Unit):ByteArray {
                if(recorded.incrementAndGet()>10)awaitCancellation()
                level(.4f);return synthetic
            }
            override suspend fun play(wav:ByteArray,device:Int,volume:Float) {Wav.decode(wav);played.incrementAndGet();delay(1)}
        }
        val store=androidx.lifecycle.ViewModelStore()
        val model=withContext(Dispatchers.Main) {nl.jarvis.mobile.features.JarvisViewModel(application,fake).also {store.put("synthetic-continuous",it)}}
        var conversation:String?=null
        try {
            application.graph.settings.save(original.copy(origin="http://127.0.0.1:8765",voiceOutput=true,automatic=true))
            withContext(Dispatchers.Main){model.active(true)}
            withTimeout(15000) {model.state.first {it.connection.authenticated&&it.naturalSettings.isNotBlank()}}
            assertFalse(model.state.value.recording)
            withContext(Dispatchers.Main){model.ptt()}
            withTimeout(120000) {while(model.state.value.messages.count {it.role=="JIJ"}<10 || model.state.value.busy || played.get()<10) {
                check(model.state.value.error.isBlank()) {model.state.value.error};delay(50)
            }}
            conversation=model.state.value.conversation
            assertNotNull(conversation);assertTrue(recorded.get()>=10);assertEquals(10,played.get())
            withContext(Dispatchers.Main){model.active(false)}
            val afterBackground=recorded.get();delay(700);assertEquals(afterBackground,recorded.get())
            val client=application.graph.api(original.copy(origin="http://127.0.0.1:8765").origin)
            assertEquals(10,client.json("/api/v1/chat/conversations/$conversation").getJSONArray("turns").length())
            assertFalse(model.state.value.recording)
            val current=client.json("/api/v1/natural/settings")
            client.json("/api/v1/natural/settings/reset","POST",JSONObject().put("revision",current.getInt("revision")).put("category","conversations"))
            client.json("/api/v1/chat/conversations/$conversation","DELETE")
            client.json("/api/v1/auth/disconnect","POST");client.forget()
        } finally {
            withContext(Dispatchers.Main){model.active(false);store.clear()}
            application.graph.settings.save(original)
        }
    }
    @Test fun syntheticBargeInCancelsPlaybackAndContinuesSameConversation() = runBlocking {
        val api=api();pair(api)
        val application=context.applicationContext as JarvisApplication
        val original=application.graph.settings.values.first()
        val base=api.json("/api/v1/natural/settings")
        api.json("/api/v1/natural/settings/listening","PATCH",JSONObject().put("revision",base.getInt("revision")).put("changes",JSONObject().put("barge_in",true)))
        suspend fun phrase(text:String):ByteArray {
            val (rate,pcm)=Wav.decode(api.synthesize(text,1f))
            val samples=java.nio.ByteBuffer.wrap(pcm).order(java.nio.ByteOrder.LITTLE_ENDIAN).asShortBuffer()
            val converted=java.nio.ByteBuffer.allocate((samples.limit().toLong()*16000/rate).toInt()*2).order(java.nio.ByteOrder.LITTLE_ENDIAN)
            repeat(converted.capacity()/2) {index->converted.putShort(samples.get((index.toLong()*rate/16000).toInt().coerceAtMost(samples.limit()-1)))}
            return Wav.encode(converted.array())
        }
        val first=phrase("Vertel iets interessants.");val interrupt=phrase("Wacht even, vertel over fietsen.")
        val recorded=java.util.concurrent.atomic.AtomicInteger();val played=java.util.concurrent.atomic.AtomicInteger()
        val paused=java.util.concurrent.atomic.AtomicInteger();val cancelled=java.util.concurrent.atomic.AtomicBoolean()
        val playbackStarted=CompletableDeferred<Unit>()
        val fake=object:AudioClient(context) {
            override fun supportsBargeIn()=true
            override fun echoReady()=true // Scheduling test, not proof of acoustic echo cancellation.
            override fun pausePlayback() {paused.incrementAndGet()}
            override fun resumePlayback() {}
            override suspend fun record(device:Int,threshold:Float,silenceMs:Int,maximumSeconds:Int,echo:Boolean,noise:Boolean,level:(Float)->Unit):ByteArray {
                when(recorded.incrementAndGet()) {
                    1->return first
                    2->{playbackStarted.await();repeat(5){level(.5f)};return interrupt}
                    else->awaitCancellation()
                }
            }
            override suspend fun play(wav:ByteArray,device:Int,volume:Float) {
                Wav.decode(wav)
                if(played.incrementAndGet()==1) {playbackStarted.complete(Unit);try {awaitCancellation()}finally {cancelled.set(true)}}
                else delay(10)
            }
        }
        val store=androidx.lifecycle.ViewModelStore()
        val model=withContext(Dispatchers.Main) {nl.jarvis.mobile.features.JarvisViewModel(application,fake).also {store.put("barge",it)}}
        try {
            application.graph.settings.save(original.copy(origin="http://127.0.0.1:8765",voiceOutput=true,automatic=true))
            withContext(Dispatchers.Main){model.active(true)}
            withTimeout(15000){model.state.first {it.connection.authenticated&&it.naturalSettings.isNotBlank()}}
            withContext(Dispatchers.Main){model.ptt()}
            withTimeout(60000) {while(model.state.value.messages.count {it.role=="JIJ"}<2 || model.state.value.busy || played.get()<2) {
                check(model.state.value.error.isBlank()){model.state.value.error};delay(50)
            }}
            assertTrue(paused.get()>0);assertTrue(cancelled.get())
            val conversation=model.state.value.conversation;assertNotNull(conversation)
            withContext(Dispatchers.Main){model.stop()}
            val client=application.graph.api("http://127.0.0.1:8765")
            assertEquals(2,client.json("/api/v1/chat/conversations/$conversation").getJSONArray("turns").length())
            val current=client.json("/api/v1/natural/settings")
            client.json("/api/v1/natural/settings/reset","POST",JSONObject().put("revision",current.getInt("revision")).put("category","listening"))
            client.json("/api/v1/chat/conversations/$conversation","DELETE")
            client.json("/api/v1/auth/disconnect","POST");client.forget()
        } finally {withContext(Dispatchers.Main){model.active(false);store.clear()};application.graph.settings.save(original)}
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
        assertTrue(audio.beginConversation())
        val capture=async {audio.record(0,echo=true,noise=true){}}
        delay(500);audio.finishRecording();withTimeout(2000){capture.await()};audio.endConversation()
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
