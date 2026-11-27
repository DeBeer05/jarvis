package nl.jarvis.mobile.device

import android.content.Intent
import android.net.Uri
import org.json.JSONObject
import java.net.URLEncoder

/** Only supported user-visible platform intents. Never claims send/call completion. */
object PhoneHandoff {
    fun label(action:String)=mapOf("dial" to "Bellen voorbereiden","sms" to "Sms opstellen","email" to "E-mail opstellen","whatsapp" to "WhatsApp openen","signal" to "Delen via Signal","navigate" to "Navigatie openen")[action] ?: "Onbekende telefoonactie"
    private fun encode(value:String)=URLEncoder.encode(value,"UTF-8").replace("+","%20")
    fun uri(action:String,target:String,text:String="",subject:String=""):String {
        require(target.length<=300 && text.length<=1800 && subject.length<=120)
        return when(action) {
            "dial","sms","whatsapp" -> {
                require(Regex("\\+?[0-9]{6,15}").matches(target))
                when(action) {"dial"->"tel:$target";"sms"->"smsto:$target";else->"https://wa.me/${target.trimStart('+')}?text=${encode(text)}"}
            }
            "email" -> {require(Regex("[^\\s@<>]+@[^\\s@<>]+\\.[^\\s@<>]+").matches(target));require(subject.none{it=='\r'||it=='\n'})
                "mailto:${encode(target)}?subject=${encode(subject)}&body=${encode(text)}"}
            "navigate" -> {require(target.isNotBlank());"geo:0,0?q=${encode(target)}"}
            else -> error("Niet-ondersteunde telefoonactie")
        }
    }
    fun intent(request:JSONObject):Intent {
        val action=request.getString("action");val target=request.optString("target");val text=request.optString("text");val subject=request.optString("subject")
        if(action=="signal") {
            require(target.isEmpty() && text.length<=1800 && subject.isEmpty())
            return Intent(Intent.ACTION_SEND).setType("text/plain").setPackage("org.thoughtcrime.securesms").putExtra(Intent.EXTRA_TEXT,text)
        }
        val intent=Intent(when(action) {"dial"->Intent.ACTION_DIAL;"sms","email"->Intent.ACTION_SENDTO;else->Intent.ACTION_VIEW},Uri.parse(uri(action,target,text,subject)))
        if(action=="sms")intent.putExtra("sms_body",text)
        return intent
    }
}
