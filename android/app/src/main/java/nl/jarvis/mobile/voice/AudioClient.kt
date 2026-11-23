package nl.jarvis.mobile.voice

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.*
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

class AudioClient(private val context: Context) {
    private val recording = AtomicBoolean(false)
    private val playing = AtomicBoolean(false)
    @Volatile private var recorder: AudioRecord? = null
    @Volatile private var track: AudioTrack? = null
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
    suspend fun record(device: Int, level: (Float) -> Unit): ByteArray = withContext(Dispatchers.IO) {
        check(context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) { "Microfoontoestemming nodig" }
        val minimum = AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        check(minimum > 0) { "Microfoonformaat niet ondersteund" }
        val input = AudioRecord(MediaRecorder.AudioSource.MIC, 16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(minimum, 4096))
        val data = ByteArrayOutputStream(); val block = ShortArray(480)
        var speech = 0; var quiet = 0; var count = 0
        try {
            check(input.state == AudioRecord.STATE_INITIALIZED) { "Microfoon niet beschikbaar" }
            if (device != 0) context.getSystemService(AudioManager::class.java).getDevices(AudioManager.GET_DEVICES_INPUTS).firstOrNull { it.id == device }?.let { input.setPreferredDevice(it) }
            recorder = input; recording.set(true); input.startRecording()
            while (recording.get() && count < 960000) {
                coroutineContext.ensureActive()
                val read = input.read(block, 0, block.size)
                if (read <= 0) { if (!recording.get()) break else error("Microfoon onderbroken") }
                val rms = sqrt(block.take(read).sumOf { (it.toDouble() / 32768) * (it.toDouble() / 32768) } / read).toFloat()
                level((rms * 8).coerceIn(0f, 1f))
                if (rms > .015) { speech += read; quiet = 0 } else quiet += read
                val bytes = ByteBuffer.allocate(read * 2).order(ByteOrder.LITTLE_ENDIAN)
                repeat(read) { bytes.putShort(block[it]) }; data.write(bytes.array()); count += read
                if ((speech >= 3360 && quiet >= 19200) || (speech < 3360 && count >= 96000)) break
            }
            if (speech < 3360) byteArrayOf() else Wav.encode(data.toByteArray())
        } finally {
            recording.set(false); recorder = null
            try { input.stop() } catch (_: IllegalStateException) { /* already stopped */ }
            input.release(); data.reset(); level(0f)
        }
    }
    suspend fun play(wav: ByteArray, device: Int) = withContext(Dispatchers.IO) {
        val (rate, pcm) = Wav.decode(wav)
        val manager=context.getSystemService(AudioManager::class.java)
        val focus=AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
            .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ASSISTANT).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
            .setOnAudioFocusChangeListener { change -> if(change==AudioManager.AUDIOFOCUS_LOSS || change==AudioManager.AUDIOFOCUS_LOSS_TRANSIENT) stop() }.build()
        check(manager.requestAudioFocus(focus)==AudioManager.AUDIOFOCUS_REQUEST_GRANTED) { "Audiofocus niet beschikbaar" }
        val audio = AudioTrack.Builder().setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ASSISTANT).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
            .setAudioFormat(AudioFormat.Builder().setSampleRate(rate).setChannelMask(AudioFormat.CHANNEL_OUT_MONO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
            .setBufferSizeInBytes(maxOf(4096, AudioTrack.getMinBufferSize(rate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT)))
            .setTransferMode(AudioTrack.MODE_STREAM).build()
        try {
            if (device != 0) context.getSystemService(AudioManager::class.java).getDevices(AudioManager.GET_DEVICES_OUTPUTS).firstOrNull { it.id == device }?.let { audio.setPreferredDevice(it) }
            track = audio; playing.set(true); audio.play()
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
