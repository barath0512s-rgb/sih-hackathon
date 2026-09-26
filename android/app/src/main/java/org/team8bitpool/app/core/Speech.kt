package org.team8bitpool.app.core

import org.json.JSONObject
import java.io.File

/**
 * On-device speech (A1): what the Api needs from the engines. The real one is
 * engine/SherpaSpeech (sherpa-onnx, JNI); unit tests use a fake.
 */
interface Speech {
    /** Recognise 16 kHz mono samples in "hi" or "sat" (loads that language's model on first use). */
    fun transcribe(lang: String, samples16k: FloatArray): String
    /** Speak `text` ("hi", or "sat" read through OlChiki.toDevanagari); a WAV in audioDir, or null. */
    fun speak(text: String, lang: String): File?
    /** Where speak() writes; served as /audio/device/<name>. */
    val audioDir: File
    /** What /health/models reports. */
    fun describe(): JSONObject
}

/** The tablet's own settings, from assets/device_config.json (tools/android/sync_config.py). */
class DeviceSettings(val onDeviceVoice: Boolean = false,
                     val threshold: Map<String, Double> = mapOf("hi" to 0.9, "sat" to 0.95),
                     val asrThreads: Int = 2,
                     val trimSilence: Map<String, Boolean> = mapOf("hi" to false, "sat" to true)) {
    companion object {
        fun from(j: JSONObject): DeviceSettings {
            fun <T> m(k: String, f: (JSONObject, String) -> T): Map<String, T> =
                j.optJSONObject(k)?.let { o -> o.keys().asSequence().associateWith { f(o, it) } } ?: emptyMap()
            return DeviceSettings(j.optBoolean("on_device_voice", false),
                m("lesson_match_threshold") { o, k -> o.getDouble(k) }, j.optInt("asr_threads", 2),
                m("asr_trim_silence") { o, k -> o.getBoolean(k) })
        }
    }
}

/** Hindi feedback spoken to the child after a spoken answer (team-authored; pending native review). */
val SPOKEN_FEEDBACK_HI = mapOf(
    "green" to "शाबाश! सही जवाब।",
    "yellow" to "लगभग सही। एक बार फिर कोशिश करो।",
    "red" to "कोई बात नहीं। फिर से सुनो और दोबारा बोलो।",
)
