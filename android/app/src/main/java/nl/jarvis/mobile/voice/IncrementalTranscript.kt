package nl.jarvis.mobile.voice

import kotlinx.coroutines.ensureActive

/** Capture-local text only. Uses the existing authenticated STT route, one request at a time. */
class IncrementalTranscript {
    var end=0;private set
    private var text=""
    companion object {
        fun merge(previous:String,current:String):String {
            val words=Regex("[\\p{L}\\p{N}_]+")
            val left=words.findAll(previous).toList();val right=words.findAll(current).toList()
            for(size in minOf(12,left.size,right.size) downTo 1) {
                if(left.takeLast(size).map{it.value.lowercase()}==right.take(size).map{it.value.lowercase()})
                    return (previous.substring(0,left[left.size-size].range.first)+current).trim()
            }
            return (previous+" "+current).trim()
        }
    }
    suspend fun request(pcm:ByteArray,recognize:suspend(ByteArray)->String):String {
        if(pcm.size<=end)return text
        val result=recognize(Wav.encode(pcm.copyOfRange(maxOf(0,end-16000),pcm.size)))
        kotlinx.coroutines.currentCoroutineContext().ensureActive()
        text=merge(text,result);end=pcm.size
        return text
    }
}
