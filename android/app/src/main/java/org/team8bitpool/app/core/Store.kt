package org.team8bitpool.app.core

import org.json.JSONObject
import java.io.File

/**
 * What the tablet records: teacher feedback (reused like database.get_correction
 * on the hub) and latency rows. JSON lines in the app's files directory; M5
 * exports them to the hub at sync.
 */
class Store(private val dir: File) {
    private val feedbackFile get() = File(dir, "feedback.jsonl")
    private val latencyFile get() = File(dir, "latency.jsonl")
    private val corrections = HashMap<String, String?>()      // "direction|key" -> text (null: thumbs-down)
    private val issued = HashMap<String, JSONObject>()

    init {
        dir.mkdirs()
        if (feedbackFile.isFile) feedbackFile.forEachLine { if (it.isNotBlank()) remember(JSONObject(it)) }
    }

    @Synchronized
    fun saveFeedback(hindi: String, santali: String, isCorrect: Boolean, corrected: String, direction: String) {
        val source = if (direction == "hi-to-sat") hindi else santali
        val row = JSONObject().put("hindi_text", hindi).put("santali_text", santali).put("is_correct", isCorrect)
            .put("corrected_text", corrected).put("direction", direction).put("source_key", TextNorm.key(source))
            .put("timestamp", System.currentTimeMillis() / 1000.0)
        feedbackFile.appendText(row.toString() + "\n")
        remember(row)
    }

    private fun remember(r: JSONObject) {
        val direction = r.getString("direction")
        val k = "$direction|${r.getString("source_key")}"
        val corrected = r.optString("corrected_text").trim()
        corrections[k] = when {
            corrected.isNotEmpty() -> corrected
            r.optBoolean("is_correct") -> (if (direction == "hi-to-sat") r.optString("santali_text")
                                           else r.optString("hindi_text")).trim().ifEmpty { null }
            else -> null
        }
    }

    /** Newest feedback wins, as on the hub. */
    @Synchronized
    fun correction(source: String, direction: String): String? = corrections["$direction|${TextNorm.key(source)}"]

    @Synchronized
    fun logLatency(rid: String, row: JSONObject) {
        issued[rid] = row
        latencyFile.appendText(JSONObject(row.toString()).put("request_id", rid).toString() + "\n")
    }

    @Synchronized
    fun reportClientTiming(rid: String, totalMs: Double, responseMs: Double, lastMs: Double?): Boolean {
        val row = issued[rid] ?: return false
        row.put("client_total_ms", totalMs).put("response_ms", responseMs).put("client_last_ms", lastMs ?: JSONObject.NULL)
        latencyFile.appendText(JSONObject().put("request_id", rid).put("client", row).toString() + "\n")
        return true
    }
}
