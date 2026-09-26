package org.team8bitpool.app.engine

import android.util.Log
import com.k2fsa.sherpa.onnx.FeatureConfig
import com.k2fsa.sherpa.onnx.OfflineModelConfig
import com.k2fsa.sherpa.onnx.OfflineNemoEncDecCtcModelConfig
import com.k2fsa.sherpa.onnx.OfflineRecognizer
import com.k2fsa.sherpa.onnx.OfflineRecognizerConfig
import com.k2fsa.sherpa.onnx.OfflineTransducerModelConfig
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsVitsModelConfig
import org.json.JSONObject
import org.team8bitpool.app.core.Audio
import org.team8bitpool.app.core.DeviceSettings
import org.team8bitpool.app.core.OlChiki
import org.team8bitpool.app.core.OnnxNmt
import org.team8bitpool.app.core.Speech
import org.team8bitpool.app.core.Translation
import java.io.File
import java.security.MessageDigest

/**
 * sherpa-onnx on the tablet (A1: M2 speech synthesis + M3 recognition), from an
 * imported model pack (tools/android/build_model_pack.py). The same models and
 * settings as the laptop run in bench/lesson_match_tune.py: Hindi NeMo CTC,
 * Santali NeMo transducer with silence trimming, greedy decoding, int8.
 * Recognisers are loaded lazily, one language at a time (the other is released
 * first), to stay inside a 2 GB tablet's memory.
 */
class SherpaSpeech(private val dir: File, private val settings: DeviceSettings, override val audioDir: File) : Speech {
    private val models = JSONObject(File(dir, "models.json").readText())
    private var recLang: String? = null
    private var rec: OfflineRecognizer? = null
    private var tts: OfflineTts? = null
    private var nmt: OnnxNmt? = null
    private fun path(rel: String) = File(dir, rel).path

    init { audioDir.mkdirs() }

    @Synchronized
    private fun recognizer(lang: String): OfflineRecognizer {
        if (recLang == lang) return rec!!
        rec?.release(); rec = null; recLang = null
        val a = models.getJSONObject("asr").getJSONObject(lang)
        val mc = when (a.getString("type")) {
            "nemo_ctc" -> OfflineModelConfig(nemo = OfflineNemoEncDecCtcModelConfig(model = path(a.getString("model"))),
                tokens = path(a.getString("tokens")), numThreads = settings.asrThreads)
            "nemo_transducer" -> OfflineModelConfig(transducer = OfflineTransducerModelConfig(
                encoder = path(a.getString("encoder")), decoder = path(a.getString("decoder")), joiner = path(a.getString("joiner"))),
                tokens = path(a.getString("tokens")), numThreads = settings.asrThreads, modelType = "nemo_transducer")
            else -> error("unknown ASR type ${a.getString("type")}")
        }
        val t0 = System.nanoTime()
        val r = OfflineRecognizer(null, OfflineRecognizerConfig(featConfig = FeatureConfig(16000, 80),
            modelConfig = mc, decodingMethod = a.optString("decoding", "greedy_search")))
        Log.i(TAG, "ASR $lang loaded in ${(System.nanoTime() - t0) / 1_000_000} ms")
        rec = r; recLang = lang
        return r
    }

    /**
     * A5: IndicTrans2 int8, loaded on first use. Memory on a 2 GB tablet: the
     * recogniser is released before translation loads (one large model at a time);
     * it reloads lazily for the next utterance.
     */
    @Synchronized
    override fun translate(text: String, direction: String): Translation? {
        if (!settings.onDeviceNmt || !File(dir, "nmt/encoder.int8.onnx").isFile) return null
        val t0 = System.nanoTime()
        val m = nmt ?: run {
            if (!settings.freeFormVoice) { rec?.release(); rec = null; recLang = null }   // 2 GB: one large model at a time
            OnnxNmt(File(dir, "nmt"), threads = settings.asrThreads).also { nmt = it; Log.i(TAG, "NMT loaded in ${(System.nanoTime() - t0) / 1_000_000} ms") }
        }
        val (src, tgt) = if (direction == "hi-to-sat") "hin_Deva" to "sat_Olck" else "sat_Olck" to "hin_Deva"
        val out = m.translate(text, src, tgt)
        return Translation(out, m.lastCut, (System.nanoTime() - t0) / 1_000_000)
    }

    @Synchronized
    private fun releaseNmt() { nmt?.close(); nmt = null }

    @Synchronized
    override fun transcribe(lang: String, samples16k: FloatArray): String {
        if (recLang != lang && !settings.freeFormVoice) releaseNmt()     // 2 GB: one large model at a time
        val x = if (settings.trimSilence[lang] == true) Audio.trimSilence(samples16k) else samples16k
        val r = recognizer(lang)
        val s = r.createStream()
        try {
            s.acceptWaveform(x, 16000)
            r.decode(s)
            return r.getResult(s).text.trim()
        } finally { s.release() }
    }

    @Synchronized
    private fun synth(): OfflineTts {
        tts?.let { return it }
        val t = models.getJSONObject("tts").getJSONObject("hi")
        val cfg = OfflineTtsConfig(model = OfflineTtsModelConfig(vits = OfflineTtsVitsModelConfig(
            model = path(t.getString("model")), tokens = path(t.getString("tokens")), dataDir = path(t.getString("data_dir")),
            noiseScale = t.getDouble("noise_scale").toFloat(), noiseScaleW = t.getDouble("noise_scale_w").toFloat(),
            lengthScale = t.getDouble("length_scale").toFloat()), numThreads = settings.asrThreads))
        val t0 = System.nanoTime()
        return OfflineTts(null, cfg).also { tts = it; Log.i(TAG, "TTS loaded in ${(System.nanoTime() - t0) / 1_000_000} ms") }
    }

    @Synchronized
    override fun speak(text: String, lang: String): File? {
        val spoken = if (lang == "sat") OlChiki.toDevanagari(text) else text
        if (spoken.isBlank()) return null
        val name = sha1("sherpa:$lang:$spoken") + ".wav"
        val f = File(audioDir, name)
        if (f.isFile && f.length() > 1024) return f
        val g = synth().generate(spoken, 0, 1.0f)
        if (g.samples.isEmpty()) return null
        val tmp = File(audioDir, "$name.tmp")
        tmp.writeBytes(Audio.wav(g.samples, g.sampleRate))
        tmp.renameTo(f)
        return f
    }

    override fun describe(): JSONObject = JSONObject()
        .put("asr", "sherpa-onnx ${models.optString("sherpa_onnx")}: Hindi NeMo CTC, Santali NeMo transducer, int8, "
            + "${settings.asrThreads} threads; loaded now: ${recLang ?: "none"}")
        .put("tts", "sherpa-onnx Piper hi voice; Santali through Ol Chiki transliteration; loaded: ${tts != null}")
        .put("nmt", if (settings.onDeviceNmt) "IndicTrans2 int8 (ONNX Runtime); loaded: ${nmt != null}" else "off")

    @Synchronized
    fun release() { rec?.release(); rec = null; recLang = null; tts?.release(); tts = null; nmt?.close(); nmt = null }

    private fun sha1(s: String) = MessageDigest.getInstance("SHA-1").digest(s.toByteArray()).joinToString("") { "%02x".format(it) }

    companion object { private const val TAG = "tablet" }
}
