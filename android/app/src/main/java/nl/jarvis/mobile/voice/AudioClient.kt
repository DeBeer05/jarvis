package nl.jarvis.mobile.voice

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.*
import android.media.audiofx.AcousticEchoCanceler
import android.media.audiofx.NoiseSuppressor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.coroutines.coroutineContext
import kotlin.math.sqrt

object Wav {
    fun encode(pcm: ByteArray, rate: Int = 16000): ByteArray {
        val b = ByteBuffer.allocate(44 + pcm.size).order(ByteOrder.LITTLE_ENDIAN)
        b.put("RIFF".toByteArray()).putInt(36 + pcm.size).put("WAVEfmt ".toByteArray()).putInt(16)
            .putShort(1).putShort(1).putInt(rate).putInt(rate * 2).putShort(2).putShort(16)
            .put("data".toByteArray()).putInt(pcm.size).put(pcm)
        return b.array()
    }
    fun decode(wav: ByteArray): Pair<Int, ByteArray> {
        require(wav.size in 44..8_000_000 && String(wav, 0, 4) == "RIFF" && String(wav, 8, 4) == "WAVE")
        val b = ByteBuffer.wrap(wav).order(ByteOrder.LITTLE_ENDIAN)
        var pos = 12; var rate = 0
        while (pos + 8 <= wav.size) {
            val id = String(wav, pos, 4); val size = b.getInt(pos + 4)
            require(size >= 0 && pos.toLong() + 8 + size <= wav.size)
            if (id == "fmt ") { require(size >= 16 && b.getShort(pos + 8).toInt() == 1 && b.getShort(pos + 10).toInt() == 1 && b.getShort(pos + 22).toInt() == 16); rate = b.getInt(pos + 12) }
            if (id == "data") { require(rate in 8000..48000); return rate to wav.copyOfRange(pos + 8, pos + 8 + size) }
            pos += 8 + size + size % 2
        }
        error("Ongeldig WAV-bestand")
    }
}

open class AudioClient(private val context: Context) {
    private val recording = AtomicBoolean(false)
    private val playing = AtomicBoolean(false)
    @Volatile private var recorder: AudioRecord? = null
    @Volatile private var track: AudioTrack? = null
    @Volatile var echoActive=false;private set
    @Volatile var noiseActive=false;private set
    var focusLost:(()->Unit)?=null
    private var previousMode:Int?=null
    fun beginConversation(): Boolean {
        if(previousMode!=null)return true
        val manager=context.getSystemService(AudioManager::class.java)
        if(manager.mode!=AudioManager.MODE_NORMAL)return false
        return try {previousMode=manager.mode;manager.mode=AudioManager.MODE_IN_COMMUNICATION;true}
        catch(_:RuntimeException){previousMode=null;false}
    }
    fun endConversation() {
        val previous=previousMode ?: return;previousMode=null
        try {val manager=context.getSystemService(AudioManager::class.java);if(manager.mode==AudioManager.MODE_IN_COMMUNICATION)manager.mode=previous}catch(_:RuntimeException){ /* Device may disappear during shutdown. */ }
    }
    fun finishRecording() { recording.set(false) }
    fun stop() {
        recording.set(false); playing.set(false)
        try { recorder?.stop() } catch (_: IllegalStateException) { /* read loop also observes cancellation */ }
        try { track?.pause(); track?.flush() } catch (_: IllegalStateException) { /* released concurrently */ }
    }
    fun devices(input: Boolean): List<Pair<Int, String>> {
        val manager = context.getSystemService(AudioManager::class.java)
        return listOf(0 to "Android-standaard") + manager.getDevices(if (input) AudioManager.GET_DEVICES_INPUTS else AudioManager.GET_DEVICES_OUTPUTS)
            .filter { it.type in setOf(AudioDeviceInfo.TYPE_BUILTIN_MIC, AudioDeviceInfo.TYPE_BUILTIN_SPEAKER, AudioDeviceInfo.TYPE_WIRED_HEADSET, AudioDeviceInfo.TYPE_USB_DEVICE, AudioDeviceInfo.TYPE_USB_HEADSET) }
            .map { it.id to it.productName.toString() }
    }
    open suspend fun record(device: Int,threshold: Float=.015f,silenceMs: Int=1200,maximumSeconds: Int=60,echo: Boolean=false,noise: Boolean=false,level: (Float) -> Unit): ByteArray = withContext(Dispatchers.IO) {
        check(context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) { "Microfoontoestemming nodig" }
        val minimum = AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        check(minimum > 0) { "Microfoonformaat niet ondersteund" }
        val input = AudioRecord(if(echo||noise)MediaRecorder.AudioSource.VOICE_COMMUNICATION else MediaRecorder.AudioSource.MIC, 16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(minimum, 4096))
        var aec:AcousticEchoCanceler?=null;var suppression:NoiseSuppressor?=null
        val data = ByteArrayOutputStream(); val block = ShortArray(480)
        var speech = 0; var quiet = 0; var count = 0
        try {
            check(input.state == AudioRecord.STATE_INITIALIZED) { "Microfoon niet beschikbaar" }
            try {if(echo&&AcousticEchoCanceler.isAvailable()) {aec=AcousticEchoCanceler.create(input.audioSessionId);aec?.enabled=true};echoActive=aec?.enabled==true}catch(_:RuntimeException){echoActive=false}
            try {if(noise&&NoiseSuppressor.isAvailable()) {suppression=NoiseSuppressor.create(input.audioSessionId);suppression?.enabled=true};noiseActive=suppression?.enabled==true}catch(_:RuntimeException){noiseActive=false}
            if (device != 0) context.getSystemService(AudioManager::class.java).getDevices(AudioManager.GET_DEVICES_INPUTS).firstOrNull { it.id == device }?.let { input.setPreferredDevice(it) }
            recorder = input; recording.set(true); input.startRecording()
            while (recording.get() && count < 16000*maximumSeconds.coerceIn(5,60)) {
                coroutineContext.ensureActive()
                val read = input.read(block, 0, block.size)
                if (read <= 0) { if (!recording.get()) break else error("Microfoon onderbroken") }
                var energy=0.0;for(index in 0 until read) {val sample=block[index].toDouble()/32768;energy+=sample*sample}
                val rms = sqrt(energy/read).toFloat()
                level((rms * 8).coerceIn(0f, 1f))
                if (rms > threshold.coerceIn(.001f,.2f)) { speech += read; quiet = 0 } else quiet += read
                val bytes = ByteBuffer.allocate(read * 2).order(ByteOrder.LITTLE_ENDIAN)
                repeat(read) { bytes.putShort(block[it]) }; data.write(bytes.array()); count += read
                if ((speech >= 3360 && quiet >= 16*silenceMs.coerceIn(200,8000)) || (speech < 3360 && count >= 96000)) break
            }
            if (speech < 3360) byteArrayOf() else Wav.encode(data.toByteArray())
        } finally {
            recording.set(false); recorder = null
            try { input.stop() } catch (_: IllegalStateException) { /* already stopped */ }
            input.release(); data.reset(); level(0f)
            aec?.release();suppression?.release();echoActive=false;noiseActive=false
        }
    }
    open suspend fun play(wav: ByteArray, device: Int,volume: Float=1f) = withContext(Dispatchers.IO) {
        val (rate, pcm) = Wav.decode(wav)
        val manager=context.getSystemService(AudioManager::class.java)
        val focus=AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
            .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ASSISTANT).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
            .setOnAudioFocusChangeListener { change -> if(change==AudioManager.AUDIOFOCUS_LOSS || change==AudioManager.AUDIOFOCUS_LOSS_TRANSIENT) {stop();focusLost?.invoke()} }.build()
        check(manager.requestAudioFocus(focus)==AudioManager.AUDIOFOCUS_REQUEST_GRANTED) { "Audiofocus niet beschikbaar" }
        val audio = AudioTrack.Builder().setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ASSISTANT).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
            .setAudioFormat(AudioFormat.Builder().setSampleRate(rate).setChannelMask(AudioFormat.CHANNEL_OUT_MONO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
            .setBufferSizeInBytes(maxOf(4096, AudioTrack.getMinBufferSize(rate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT)))
            .setTransferMode(AudioTrack.MODE_STREAM).build()
        try {
            if (device != 0) context.getSystemService(AudioManager::class.java).getDevices(AudioManager.GET_DEVICES_OUTPUTS).firstOrNull { it.id == device }?.let { audio.setPreferredDevice(it) }
            track = audio; playing.set(true);audio.setVolume(volume.coerceIn(0f,1f)); audio.play()
            var offset = 0
            while (offset < pcm.size && playing.get()) {
                coroutineContext.ensureActive()
                val wrote = audio.write(pcm, offset, minOf(1024, pcm.size - offset), AudioTrack.WRITE_BLOCKING)
                if (wrote <= 0 && !playing.get()) break
                check(wrote > 0) { "Luidspreker niet beschikbaar" }; offset += wrote
            }
            while(playing.get() && audio.playbackHeadPosition < pcm.size/2) { coroutineContext.ensureActive(); kotlinx.coroutines.delay(10) }
        } finally { playing.set(false); track = null; audio.release(); manager.abandonAudioFocusRequest(focus) }
    }
}
