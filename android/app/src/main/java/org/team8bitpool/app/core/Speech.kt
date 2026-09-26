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
    /** A5: translate a new sentence on the tablet; null when translation is not installed or not enabled. */
    fun translate(text: String, direction: String): Translation? = null
}

class Translation(val text: String, val needsReview: Boolean, val ms: Long)

/** The tablet's own settings, from assets/device_config.json (tools/android/sync_config.py). */
class DeviceSettings(val onDeviceVoice: Boolean = false,
                     val threshold: Map<String, Double> = mapOf("hi" to 0.9, "sat" to 0.95),
                     val asrThreads: Int = 2,
                     val trimSilence: Map<String, Boolean> = mapOf("hi" to false, "sat" to true),
                     val onDeviceNmt: Boolean = false,
                     /** A5: free-form speech is translated on the tablet (flag on AND enough RAM, decided at start-up). */
                     val freeFormVoice: Boolean = false) {
    companion object {
        /** totalRamBytes: the device's RAM (ActivityManager.MemoryInfo.totalMem); 0 = unknown. */
        fun from(j: JSONObject, totalRamBytes: Long = 0): DeviceSettings {
            fun <T> m(k: String, f: (JSONObject, String) -> T): Map<String, T> =
                j.optJSONObject(k)?.let { o -> o.keys().asSequence().associateWith { f(o, it) } } ?: emptyMap()
            return DeviceSettings(j.optBoolean("on_device_voice", false),
                m("lesson_match_threshold") { o, k -> o.getDouble(k) }, j.optInt("asr_threads", 2),
                m("asr_trim_silence") { o, k -> o.getBoolean(k) }, j.optBoolean("on_device_nmt", false),
                j.optBoolean("on_device_nmt", false) && j.optBoolean("free_form_voice", false) &&
                    totalRamBytes >= (j.optDouble("free_form_voice_min_ram_gb", 3.5) * (1L shl 30)).toLong())
        }
    }
}

/** Hindi feedback spoken to the child after a spoken answer (team-authored; pending native review). */
val SPOKEN_FEEDBACK_HI = mapOf(
    "green" to "शाबाश! सही जवाब।",
    "yellow" to "लगभग सही। एक बार फिर कोशिश करो।",
    "red" to "कोई बात नहीं। फिर से सुनो और दोबारा बोलो।",
)
