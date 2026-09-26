package org.team8bitpool.app.core

import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Audio helpers for the on-device voice path (A1). Pure Kotlin, unit-tested. */
object Audio {
    class Pcm(val samples: FloatArray, val sampleRate: Int)

    /**
     * A RIFF/WAVE file with 16-bit PCM (what MicBridge and the page's NativeRecorder
     * send) -> mono float samples. Null for anything else (the tablet does not
     * decode compressed audio).
     */
    fun decodeWav(b: ByteArray): Pcm? {
        if (b.size < 44 || String(b, 0, 4, Charsets.US_ASCII) != "RIFF" || String(b, 8, 4, Charsets.US_ASCII) != "WAVE") return null
        val bb = ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN)
        var pos = 12
        var channels = 0; var rate = 0; var bits = 0; var format = 0
        while (pos + 8 <= b.size) {
            val id = String(b, pos, 4, Charsets.US_ASCII)
            val len = bb.getInt(pos + 4)
            val body = pos + 8
            if (id == "fmt ") {
                format = bb.getShort(body).toInt(); channels = bb.getShort(body + 2).toInt()
                rate = bb.getInt(body + 4); bits = bb.getShort(body + 14).toInt()
            } else if (id == "data") {
                if (format != 1 || bits != 16 || channels < 1) return null
                val end = minOf(b.size, body + (if (len < 0) b.size else len))
                val frames = (end - body) / (2 * channels)
                val out = FloatArray(frames)
                for (i in 0 until frames) {
                    var s = 0f
                    for (c in 0 until channels) s += bb.getShort(body + 2 * (i * channels + c)) / 32768f
                    out[i] = s / channels
                }
                return Pcm(out, rate)
            }
            pos = body + len + (len and 1)
            if (len < 0) break
        }
        return null
    }

    /** 16-bit PCM mono WAV bytes. */
    fun wav(samples: FloatArray, rate: Int): ByteArray {
        val bb = ByteBuffer.allocate(44 + samples.size * 2).order(ByteOrder.LITTLE_ENDIAN)
        bb.put("RIFF".toByteArray()).putInt(36 + samples.size * 2).put("WAVE".toByteArray())
        bb.put("fmt ".toByteArray()).putInt(16).putShort(1).putShort(1).putInt(rate).putInt(rate * 2).putShort(2).putShort(16)
        bb.put("data".toByteArray()).putInt(samples.size * 2)
        for (s in samples) bb.putShort((s.coerceIn(-1f, 1f) * 32767f).toInt().toShort())
        return bb.array()
    }

    /**
     * Port of indicconformer_asr.trim_silence: drop leading and trailing silence.
     * A frame is speech if its RMS is within |floorDb| of the loudest frame; the kept
     * region is padded by keepMs (before, after). Unchanged if no speech is found.
     */
    fun trimSilence(x: FloatArray, sr: Int = 16000, frameMs: Int = 20, floorDb: Double = -40.0,
                    keepBeforeMs: Int = 150, keepAfterMs: Int = 200): FloatArray {
        val n = sr * frameMs / 1000
        if (n <= 0 || x.size < 2 * n) return x
        val frames = x.size / n
        val rms = DoubleArray(frames) { f ->
            var s = 0.0
            for (i in f * n until (f + 1) * n) s += x[i].toDouble() * x[i]
            Math.sqrt(s / n) + 1e-10
        }
        val max = rms.maxOrNull() ?: return x
        var first = -1; var last = -1
        for (f in 0 until frames) if (20 * Math.log10(rms[f] / max) > floorDb) { if (first < 0) first = f; last = f }
        if (first < 0) return x
        val start = maxOf(0, first * n - sr * keepBeforeMs / 1000)
        val end = minOf(x.size, (last + 1) * n + sr * keepAfterMs / 1000)
        return x.copyOfRange(start, end)
    }

    /** Linear resampling to 16 kHz (only used if a recording is not already 16 kHz). */
    fun to16k(p: Pcm): FloatArray {
        if (p.sampleRate == 16000) return p.samples
        val ratio = p.sampleRate / 16000.0
        val n = (p.samples.size / ratio).toInt()
        return FloatArray(n) { i ->
            val t = i * ratio; val j = t.toInt(); val f = (t - j).toFloat()
            val a = p.samples[minOf(j, p.samples.size - 1)]; val b = p.samples[minOf(j + 1, p.samples.size - 1)]
            a + (b - a) * f
        }
    }
}

/** A minimal multipart/form-data reader for the page's FormData uploads. */
object Multipart {
    class Part(val name: String, val filename: String?, val data: ByteArray) {
        fun text() = String(data, Charsets.UTF_8)
    }

    fun parse(body: ByteArray, contentType: String): Map<String, Part> {
        val boundary = Regex("boundary=\"?([^\";]+)\"?").find(contentType)?.groupValues?.get(1) ?: return emptyMap()
        val delim = "--$boundary".toByteArray(Charsets.ISO_8859_1)
        val out = LinkedHashMap<String, Part>()
        var i = indexOf(body, delim, 0)
        while (i >= 0) {
            var start = i + delim.size
            if (start + 1 < body.size && body[start] == '-'.code.toByte() && body[start + 1] == '-'.code.toByte()) break
            if (start + 1 < body.size && body[start] == '\r'.code.toByte()) start += 2
            val headEnd = indexOf(body, "\r\n\r\n".toByteArray(), start)
            if (headEnd < 0) break
            val headers = String(body, start, headEnd - start, Charsets.UTF_8)
            val next = indexOf(body, delim, headEnd + 4)
            if (next < 0) break
            var dataEnd = next
            if (dataEnd >= 2 && body[dataEnd - 2] == '\r'.code.toByte() && body[dataEnd - 1] == '\n'.code.toByte()) dataEnd -= 2
            val disp = headers.lines().firstOrNull { it.lowercase().startsWith("content-disposition") } ?: ""
            val name = Regex("\\bname=\"([^\"]*)\"").find(disp)?.groupValues?.get(1)
            val filename = Regex("filename=\"([^\"]*)\"").find(disp)?.groupValues?.get(1)
            if (name != null) out[name] = Part(name, filename, body.copyOfRange(headEnd + 4, dataEnd))
            i = next
        }
        return out
    }

    private fun indexOf(h: ByteArray, n: ByteArray, from: Int): Int {
        outer@ for (i in from..h.size - n.size) {
            for (j in n.indices) if (h[i + j] != n[j]) continue@outer
            return i
        }
        return -1
    }
}
