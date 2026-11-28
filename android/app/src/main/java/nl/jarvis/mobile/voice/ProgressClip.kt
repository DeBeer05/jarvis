package nl.jarvis.mobile.voice

import java.io.File
import java.security.MessageDigest

data class ProgressClip(val id:String,val voiceKey:String,val checksum:String,val text:String) {
    init {
        require(id.matches(Regex("[a-z]+-[0-9]{2}")))
        require(voiceKey.matches(Regex("[a-f0-9]{32}")))
        require(checksum.matches(Regex("[a-f0-9]{64}")))
        require(text.length<=200)
    }
}

class ProgressCache(private val root:File) {
    private fun hash(raw:ByteArray)=MessageDigest.getInstance("SHA-256").digest(raw).joinToString(""){"%02x".format(it)}
    private fun file(origin:String,clip:ProgressClip)=File(File(File(root,hash(origin.toByteArray()).take(24)),clip.voiceKey),clip.id+".wav")
    fun get(origin:String,clip:ProgressClip):ByteArray? {
        val target=file(origin,clip)
        if(!target.isFile || target.length() !in 44..800000)return null
        val raw=target.readBytes()
        return raw.takeIf {hash(it)==clip.checksum}
    }
    fun put(origin:String,clip:ProgressClip,raw:ByteArray) {
        require(raw.size in 44..800000 && hash(raw)==clip.checksum)
        val target=file(origin,clip);check(target.parentFile!!.isDirectory || target.parentFile!!.mkdirs())
        val pending=File(target.path+".pending");pending.writeBytes(raw)
        check(pending.renameTo(target))
        root.walkTopDown().filter {it.isFile&&it.extension=="wav"}.sortedByDescending {it.lastModified()}.drop(300).forEach {it.delete()}
    }
}
