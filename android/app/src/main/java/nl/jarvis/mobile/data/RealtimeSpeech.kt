package nl.jarvis.mobile.data

import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeout
import okhttp3.*
import okio.ByteString.Companion.toByteString
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/** A foreground authenticated socket. Recognition never submits chat actions. */
class RealtimeSpeech(client:OkHttpClient,private val origin:String) {
    private val http=client.newBuilder().pingInterval(20,TimeUnit.SECONDS).build()
    private val serial=Mutex()
    @Volatile private var socket:WebSocket?=null
    @Volatile private var messages:Channel<JSONObject>?=null
    fun close() {socket?.cancel();socket=null;messages?.close();messages=null}
    suspend fun transcribe(wav:ByteArray,token:String):String=serial.withLock {
        try {
            if(socket==null) {
                val channel=Channel<JSONObject>(8);messages=channel
                val request=Request.Builder().url(origin+"/api/v1/realtime").header("Authorization","Bearer $token").build()
                socket=http.newWebSocket(request,object:WebSocketListener() {
                    override fun onMessage(webSocket:WebSocket,text:String) {
                        if(text.length>65536){webSocket.cancel();channel.close();return}
                        try {if(!channel.trySend(JSONObject(text)).isSuccess){webSocket.cancel();channel.close()}}
                        catch(_:Exception){webSocket.cancel();channel.close()}
                    }
                    override fun onFailure(webSocket:WebSocket,error:Throwable,response:Response?) {channel.close(error)}
                    override fun onClosed(webSocket:WebSocket,code:Int,reason:String) {channel.close()}
                })
                check(withTimeout(5000){channel.receive()}.optString("type")=="ready")
            }
            val active=socket ?: error("Spraakverbinding verbroken");val channel=messages ?: error("Spraakverbinding verbroken")
            check(active.send(JSONObject().put("type","audio.start").toString()))
            check(withTimeout(5000){channel.receive()}.optString("type")=="audio.ready")
            for(offset in wav.indices step 32768)check(active.send(wav.copyOfRange(offset,minOf(offset+32768,wav.size)).toByteString()))
            check(active.send(JSONObject().put("type","audio.commit").toString()))
            val result=withTimeout(110000){channel.receive()}
            check(result.optString("type")=="transcript" && result.optBoolean("final"))
            result.getString("text")
        }catch(error:Throwable){close();throw error}
    }
}
