package nl.jarvis.mobile.device

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.BatteryManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import nl.jarvis.mobile.data.JarvisApi
import org.json.JSONObject

object DeviceSnapshot {
    private val lock=Mutex()
    private val previous=linkedMapOf<String,Pair<String,Long>>()
    @android.annotation.SuppressLint("MissingPermission") // Runtime grant checked immediately before last-known data.
    suspend fun send(context:Context,api:JarvisApi,settings:JSONObject)=lock.withLock {withContext(Dispatchers.IO) {
        val body=JSONObject()
        if(settings.optBoolean("status_allowed")) {
            val battery=context.registerReceiver(null,IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            val level=battery?.getIntExtra(BatteryManager.EXTRA_LEVEL,-1) ?: -1
            val scale=battery?.getIntExtra(BatteryManager.EXTRA_SCALE,-1) ?: -1
            if(level>=0 && scale>0)body.put("battery",(100L*level/scale).toInt().coerceIn(0,100))
            val status=battery?.getIntExtra(BatteryManager.EXTRA_STATUS,-1) ?: -1
            if(status>=0)body.put("charging",status in setOf(BatteryManager.BATTERY_STATUS_CHARGING,BatteryManager.BATTERY_STATUS_FULL))
        }
        if(settings.optBoolean("notification_allowed")) {
            val packages=settings.optJSONArray("notification_packages")
            val allowed=if(packages==null)emptySet() else (0 until packages.length()).map{packages.getString(it)}.toSet()
            JarvisNotificationListener.counts(allowed)?.let{body.put("notifications",it)}
        }
        if(settings.optBoolean("location_allowed") && (context.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED || context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED)) {
            val manager=context.getSystemService(LocationManager::class.java)
            val location=manager.getProviders(true).mapNotNull {provider ->runCatching{manager.getLastKnownLocation(provider)}.getOrNull()}.maxByOrNull{it.time}
            if(location!=null && location.time>=System.currentTimeMillis()-86_400_000 && location.hasAccuracy()) {
                body.put("location",JSONObject().put("latitude",location.latitude).put("longitude",location.longitude)
                    .put("accuracy_m",location.accuracy).put("sampled_at",location.time/1000.0))
            }
        }
        if(body.length()>0) {
            val key=api.endpoint.origin+":"+api.generation
            val hash=java.security.MessageDigest.getInstance("SHA-256").digest(body.toString().toByteArray()).joinToString(""){"%02x".format(it)}
            val now=android.os.SystemClock.elapsedRealtime();val last=previous[key]
            if(last==null || now-last.second>=10000 && (last.first!=hash || now-last.second>=120000)) {
                api.json("/api/v1/natural/device-status","POST",body)
                previous[key]=hash to now
                while(previous.size>8)previous.remove(previous.keys.first())
            }
        }
        Unit
    }}
}
