package org.team8bitpool.app.core

import org.json.JSONObject
import java.io.File

/**
 * What the tablet records: teacher feedback (reused like database.get_correction
 * on the hub), latency rows, and class-level lesson counts (A4: which lesson was
 * taught, and how many answers were green / yellow / red; never a child's name or
 * voice). JSON lines in the app's files directory. exportSigned() writes the file
 * the hub merges (sync.py), signed with this tablet's own Ed25519 key.
 */
class Store(private val dir: File) {
    private val feedbackFile get() = File(dir, "feedback.jsonl")
    private val latencyFile get() = File(dir, "latency.jsonl")
    private val classFile get() = File(dir, "class.jsonl")
    private val keyFile get() = File(dir, "device.key")
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

    /** This tablet's Ed25519 key (made once, kept in the app's private files). */
    private val deviceKey: ByteArray by lazy {
        if (!keyFile.isFile) keyFile.writeBytes(ByteArray(32).also { java.security.SecureRandom().nextBytes(it) })
        keyFile.readBytes()
    }
    val publicKey: ByteArray by lazy { Ed25519.publicKey(deviceKey) }
    /** A short stable id: the first 16 hex digits of SHA-256 of the public key. */
    val deviceId: String by lazy {
        Ed25519.hex(java.security.MessageDigest.getInstance("SHA-256").digest(publicKey)).substring(0, 16)
    }

    private fun day() = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.ROOT).format(java.util.Date())

    /** A lesson started (A4 counts; A8 view). */
    @Synchronized
    fun logSession(grade: String, topic: String, lakshya: org.json.JSONArray) = classFile.appendText(
        JSONObject().put("day", day()).put("grade", grade).put("topic", topic).put("lakshya_ids", lakshya)
            .put("event", "session").toString() + "\n")

    /** An answer was graded: only the signal is kept. */
    @Synchronized
    fun logAnswer(grade: String, topic: String, lakshya: org.json.JSONArray, signal: String) = classFile.appendText(
        JSONObject().put("day", day()).put("grade", grade).put("topic", topic).put("lakshya_ids", lakshya)
            .put("event", "answer").put("signal", signal).toString() + "\n")

    /** Per day and lesson: sessions, green, yellow, red. */
    @Synchronized
    fun classCounts(): List<JSONObject> {
        val m = LinkedHashMap<String, JSONObject>()
        if (classFile.isFile) classFile.forEachLine { line ->
            if (line.isBlank()) return@forEachLine
            val e = JSONObject(line)
            val k = "${e.getString("day")}|${e.getString("grade")}|${e.getString("topic")}"
            val row = m.getOrPut(k) {
                JSONObject().put("day", e.getString("day")).put("grade", e.getString("grade")).put("topic", e.getString("topic"))
                    .put("lakshya_ids", e.optJSONArray("lakshya_ids") ?: org.json.JSONArray())
                    .put("sessions", 0).put("green", 0).put("yellow", 0).put("red", 0)
            }
            val f = if (e.getString("event") == "session") "sessions" else e.optString("signal")
            if (row.has(f)) row.put(f, row.getInt(f) + 1)
        }
        return m.values.toList()
    }

    /** The signed file for the hub (format: sync.py). */
    @Synchronized
    fun exportSigned(): ByteArray {
        val corrections = org.json.JSONArray()
        if (feedbackFile.isFile) feedbackFile.forEachLine { if (it.isNotBlank()) corrections.put(JSONObject(it)) }
        val pub = Ed25519.hex(publicKey)
        val payload = JSONObject().put("format", 1).put("kind", "tablet-export").put("device_id", deviceId)
            .put("public_key", pub)
            .put("created", java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", java.util.Locale.ROOT).format(java.util.Date()))
            .put("corrections", corrections).put("analytics", org.json.JSONArray(classCounts())).toString()
        val sig = Ed25519.sign(deviceKey, payload.toByteArray(Charsets.UTF_8))
        return JSONObject().put("payload", payload).put("signature", Ed25519.hex(sig)).put("public_key", pub)
            .toString().toByteArray(Charsets.UTF_8)
    }

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
