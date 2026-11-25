package nl.jarvis.mobile.voice

/** Conservative transcript guard supplements platform AEC; it grants no authority. */
object EchoGuard {
    fun resemblesOutput(text: String,spoken: String): Boolean {
        fun words(value: String)=Regex("[\\p{L}\\p{N}_]+").findAll(value.lowercase()).map{it.value}.toList()
        val candidate=words(text);val reference=words(spoken)
        if(candidate.isEmpty())return true
        if(candidate.size<=2 && candidate.all {it in reference})return true
        if(candidate.size<3)return false
        return (0..maxOf(0,reference.size-candidate.size)).any {start ->
            candidate.indices.count {index -> reference.getOrNull(start+index)==candidate[index]}.toDouble()/candidate.size>=.85
        }
    }
}
