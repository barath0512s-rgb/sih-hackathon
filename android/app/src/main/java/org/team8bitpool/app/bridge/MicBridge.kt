package org.team8bitpool.app.bridge

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Base64
import android.webkit.JavascriptInterface
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Native microphone for the page: 16 kHz mono 16-bit PCM from AudioRecord,
 * returned as a base64 WAV. frontend.html uses it when `window.VaaniMic`
 * exists, and MediaRecorder otherwise (the hub in a browser).
 */
class MicBridge(private val hasPermission: () -> Boolean, private val askPermission: () -> Unit) {
    private var recorder: AudioRecord? = null
    private var thread: Thread? = null
    private val pcm = ByteArrayOutputStream()
    @Volatile private var level = 0.0

    @JavascriptInterface
    fun available(): Boolean = hasPermission().also { if (!it) askPermission() }

    @SuppressLint("MissingPermission")
    @JavascriptInterface
    @Synchronized
    fun start(): Boolean {
        if (!hasPermission()) { askPermission(); return false }
        if (recorder != null) return true
        val min = AudioRecord.getMinBufferSize(RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val r = AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, RATE, AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT, maxOf(min, RATE))   // at least 0.5 s of buffer
        if (r.state != AudioRecord.STATE_INITIALIZED) { r.release(); return false }
        synchronized(pcm) { pcm.reset() }
        recorder = r
        r.startRecording()
        thread = Thread {
            val buf = ShortArray(RATE / 50)                    // 20 ms frames
            val bytes = ByteBuffer.allocate(buf.size * 2).order(ByteOrder.LITTLE_ENDIAN)
            while (recorder === r) {
                val n = r.read(buf, 0, buf.size)
                if (n <= 0) continue
                bytes.clear()
                var sum = 0.0
                for (i in 0 until n) { bytes.putShort(buf[i]); sum += buf[i] * buf[i].toDouble() }
                level = Math.sqrt(sum / n) / 32768.0
                synchronized(pcm) { pcm.write(bytes.array(), 0, n * 2) }
            }
        }.apply { name = "mic"; start() }
        return true
    }

    /** RMS of the last 20 ms frame, 0..1, for the page's level meter and endpointing. */
    @JavascriptInterface
    fun level(): Double = level

    /** Stops and returns the recording as base64 WAV ("" if nothing was recorded). */
    @JavascriptInterface
    @Synchronized
    fun stop(): String {
        val r = recorder ?: return ""
        recorder = null
        thread?.join(500)
        r.stop(); r.release()
        val data = synchronized(pcm) { pcm.toByteArray() }
        if (data.isEmpty()) return ""
        return Base64.encodeToString(wav(data), Base64.NO_WRAP)
    }

    companion object {
        const val RATE = 16000

        fun wav(pcm16: ByteArray): ByteArray {
            val h = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
            h.put("RIFF".toByteArray()).putInt(36 + pcm16.size).put("WAVE".toByteArray())
            h.put("fmt ".toByteArray()).putInt(16).putShort(1).putShort(1).putInt(RATE).putInt(RATE * 2)
                .putShort(2).putShort(16)
            h.put("data".toByteArray()).putInt(pcm16.size)
            return h.array() + pcm16
        }
    }
}
