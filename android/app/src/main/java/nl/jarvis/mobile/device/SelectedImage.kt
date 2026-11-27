package nl.jarvis.mobile.device

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Rect
import android.net.Uri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream

/** User-picked image only. No MediaProjection, storage permission or background capture. */
object SelectedImage {
    suspend fun read(context:Context,uri:Uri):ByteArray=withContext(Dispatchers.IO) {
        val raw=ByteArrayOutputStream()
        context.contentResolver.openInputStream(uri)?.use {input ->
            val block=ByteArray(8192)
            while(true) {val count=input.read(block);if(count<0)break
                require(raw.size()+count<=8_000_000){"Kies een afbeelding van maximaal 8 MB"};raw.write(block,0,count)}
        } ?: error("Afbeelding niet beschikbaar")
        val bytes=raw.toByteArray();val bounds=BitmapFactory.Options().apply{inJustDecodeBounds=true}
        BitmapFactory.decodeByteArray(bytes,0,bytes.size,bounds)
        require(bounds.outWidth>0 && bounds.outHeight>0 && bounds.outWidth.toLong()*bounds.outHeight<=50_000_000){"Afbeeldingsformaat niet ondersteund"}
        val options=BitmapFactory.Options()
        while(bounds.outWidth/options.inSampleSize.coerceAtLeast(1)>2048 || bounds.outHeight/options.inSampleSize.coerceAtLeast(1)>2048)options.inSampleSize=options.inSampleSize.coerceAtLeast(1)*2
        val original=BitmapFactory.decodeByteArray(bytes,0,bytes.size,options) ?: error("Afbeelding kon niet worden gelezen")
        try {
            for(maximum in listOf(1600,960,640)) {
                val ratio=minOf(1.0,maximum.toDouble()/maxOf(original.width,original.height))
                val image=Bitmap.createBitmap(maxOf(1,(original.width*ratio).toInt()),maxOf(1,(original.height*ratio).toInt()),Bitmap.Config.ARGB_8888)
                try {
                    Canvas(image).drawBitmap(original,null,Rect(0,0,image.width,image.height),null)
                    val output=ByteArrayOutputStream();check(image.compress(Bitmap.CompressFormat.PNG,100,output))
                    if(output.size()<=1_800_000 && image.width.toLong()*image.height<=2_097_152)return@withContext output.toByteArray()
                }finally{image.recycle()}
            }
            error("Afbeelding blijft te groot")
        }finally{original.recycle()}
    }
}
