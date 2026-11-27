package nl.jarvis.mobile

import org.json.JSONObject

/** Visibility is supplied by the backend contract; hidden settings stay intact. */
fun voiceFieldVisible(field:JSONObject,voice:JSONObject):Boolean {
    val rule=field.optJSONObject("x-voice-visible") ?: return true
    val mode=voice.optString("mode")
    val premium=mode !in setOf("local","offline") && (voice.optString("tts_provider")=="elevenlabs" || mode in setOf("premium","budget"))
    val model=if(mode=="budget")"eleven_flash_v2_5" else voice.optString("elevenlabs_model")
    val excluded=rule.optJSONArray("exclude_modes")
    if(excluded!=null && (0 until excluded.length()).any {excluded.getString(it)==mode})return false
    if(rule.has("premium") && rule.getBoolean("premium")!=premium)return false
    for(key in listOf("models","speed_models")) {
        val values=rule.optJSONArray(key)
        if(premium && values!=null && (0 until values.length()).none {values.getString(it)==model})return false
    }
    return true
}
