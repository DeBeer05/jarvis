package nl.jarvis.mobile.voice

/** Pure text signal; it never sends chat or executes an action. */
object TurnBoundary {
    fun complete(text:String):Boolean {
        val words=Regex("[\\p{L}\\p{N}_]+").findAll(text.lowercase()).map{it.value}.toList()
        if(words.isEmpty())return false
        if(words.last() in setOf("eh","ehm","uh","uhm","en","maar","of","om","voor","met","naar","een","de","het","mijn","jouw","dat","dus","want","als","dan"))return false
        if(text.count{it=='('}!=text.count{it==')'})return false
        if(Regex("\\b(maak|plan|verzet|verplaats)\\b.*\\b(afspraak|vergadering)\\b",RegexOption.IGNORE_CASE).containsMatchIn(text)) {
            if(!Regex("\\b\\d{1,2}:\\d{2}\\b|\\b(om|van|tussen)\\s+(\\d+|een|twee|drie|vier|vijf|zes|zeven|acht|negen|tien|elf|twaalf|half|kwart)\\b",RegexOption.IGNORE_CASE).containsMatchIn(text))return false
        }
        return true
    }
}
