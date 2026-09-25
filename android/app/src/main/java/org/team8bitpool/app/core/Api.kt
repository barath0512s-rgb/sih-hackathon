package org.team8bitpool.app.core

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

class Resp(val status: Int, val type: String, val body: ByteArray) {
    companion object {
        fun json(o: JSONObject, status: Int = 200) = Resp(status, "application/json", o.toString().toByteArray())
        fun error(status: Int, msg: String, code: String? = null) =
            json(JSONObject().put("error", msg).apply { if (code != null) put("code", code) }, status)
        fun file(f: File, type: String) = Resp(200, type, f.readBytes())
    }
}

/** Which engines run on this device. M1: none (content comes from the pack). */
data class Engines(val asr: Boolean = false, val nmt: Boolean = false, val tts: Boolean = false)

/**
 * The hub's REST API (app.py), answered on the tablet. Contract:
 * contract/rest_contract.json. Everything a missing engine would be needed for
 * is refused with 503 and code "engine_not_on_device", never faked.
 */
class Api(
    private val packProvider: () -> Pack?,
    private val store: Store,
    private val engines: Engines = Engines(),
    private val defaultConfig: JSONObject = JSONObject().put("app_name", "").put("app_name_local", JSONObject()),
) {
    private val sessions = HashMap<String, LessonSession>()
    private val directions = setOf("hi-to-sat", "sat-to-hi")
    private val signalMessages = mapOf(
        "green" to "Correct — student understood",
        "yellow" to "Partial — try again",
        "red" to "Incorrect — repeat the concept",
    )

    private fun notOnDevice(what: String) = Resp.error(503, "$what is not on this tablet yet", "engine_not_on_device")
    private fun noPack() = Resp.error(503, "No content pack yet: import one (Settings → Content pack)", "no_content_pack")

    fun handle(method: String, path: String, query: Map<String, String>, body: ByteArray?, contentType: String?): Resp {
        val json = if (contentType?.startsWith("application/json") == true && body != null && body.isNotEmpty())
            runCatching { JSONObject(String(body, Charsets.UTF_8)) }.getOrNull() ?: JSONObject() else JSONObject()
        val pack = packProvider()
        return when ("$method $path") {
            "GET /config" -> Resp.json(pack?.config ?: defaultConfig)
            "GET /health" -> Resp.json(JSONObject().put("status", "ok").put("device", "Android"))
            "GET /health/models" -> Resp.json(healthModels(pack))
            "GET /lessons" -> Resp.json(pack?.lessonsApi ?: JSONObject().put("lessons", JSONArray()))
            "GET /flashcards" -> flashcards(pack, query)
            "POST /session/start" -> sessionStart(pack, json)
            "POST /session/next" -> withSession(json) { s ->
                s.advance()
                if (s.currentStep == null) Resp.json(JSONObject().put("completed", true).put("session_id", s.sid))
                else Resp.json(JSONObject().put("completed", false).put("session_id", s.sid)
                    .put("step_index", s.stepIdx).put("total_steps", s.totalSteps).put("step", s.currentStep))
            }
            "POST /session/goto" -> withSession(json) { s ->
                val step = json.opt("step")
                val n = (step as? Number)?.toInt() ?: (step as? String)?.toIntOrNull()
                    ?: return@withSession Resp.error(400, "Bad step")
                s.goto(n)
                Resp.json(JSONObject().put("step_index", s.stepIdx).put("total_steps", s.totalSteps).put("step", s.currentStep))
            }
            "POST /session/response" -> sessionResponse(json, contentType)
            "POST /session/summary" -> withSession(json) { s -> Resp.json(s.summary()) }
            "POST /translate/text" -> translateText(pack, json)
            "POST /translate/audio", "POST /translate/audio_stream" -> notOnDevice("Speech recognition")
            "POST /speak" -> speak(pack, json)
            "POST /feedback" -> feedback(json)
            "POST /metrics/client" -> metricsClient(json)
            "POST /worksheet" -> worksheet(pack, json)
            "POST /curriculum/import", "POST /curriculum/save" ->
                Resp.error(501, "Lessons are written on the hub and arrive in the content pack", "hub_only")
            else -> when {
                method == "GET" && path.startsWith("/audio/pack/") -> packAudio(pack, path.removePrefix("/audio/pack/"))
                else -> Resp.error(404, "Not found")
            }
        }
    }

    private fun healthModels(pack: Pack?): JSONObject {
        fun lang(tts: String) = JSONObject()
            .put("asr", JSONObject().put("engine", if (engines.asr) "on device" else "not on device yet (M3)"))
            .put("nmt", JSONObject().put("engine", if (engines.nmt) "on device"
                else "not on device yet (M4); lesson lines come from the content pack"))
            .put("tts", JSONObject().put("engine", if (engines.tts) "on device"
                else "not on device yet (M2); $tts audio comes from the content pack"))
        return JSONObject()
            .put("languages", JSONObject().put("hi", lang("Hindi")).put("sat", lang("Santali")))
            .put("online_dependencies", JSONArray())
            .put("content_pack", pack?.manifest?.let {
                JSONObject().put("created", it.optString("created")).put("counts", it.optJSONObject("counts"))
                    .put("model_versions", it.optJSONObject("model_versions"))
            } ?: JSONObject.NULL)
            .put("active_sessions", sessions.size)
    }

    private fun flashcards(pack: Pack?, q: Map<String, String>): Resp {
        pack ?: return Resp.json(JSONObject().put("decks", JSONArray()))
        val grade = q["grade"]; val topic = q["topic"]
        val decks = JSONArray()
        val all = pack.flashcardsApi.getJSONArray("decks")
        for (i in 0 until all.length()) {
            val d = JSONObject(all.getJSONObject(i).toString())
            if (grade != null && d.getString("grade") != grade) continue
            if (topic != null && d.getString("topic") != topic) continue
            val cards = d.getJSONArray("cards")
            for (j in 0 until cards.length()) {            // a teacher's correction on this tablet wins
                val c = cards.getJSONObject(j)
                store.correction(c.getString("hi"), "hi-to-sat")?.let {
                    c.put("sat", it).put("source", "teacher").put("review_status", "teacher_verified")
                }
            }
            decks.put(d)
        }
        if ((grade != null || topic != null) && decks.length() == 0) return Resp.error(404, "No lesson matches that grade and topic")
        return Resp.json(JSONObject().put("decks", decks))
    }

    private fun sessionStart(pack: Pack?, d: JSONObject): Resp {
        pack ?: return noPack()
        val grade = d.opt("grade")?.toString() ?: "2"
        val topic = d.optString("topic", "addition")
        val lesson = pack.lesson(grade, topic) ?: return Resp.error(404, "Lesson not found")
        val sid = UUID.randomUUID().toString().replace("-", "")
        val s = LessonSession(sid, grade, topic, lesson)
        synchronized(sessions) { sessions[sid] = s }
        return Resp.json(JSONObject().put("session_id", sid).put("title", lesson.getString("title"))
            .put("competency", lesson.optString("competency")).put("lakshya_ids", lesson.optJSONArray("lakshya_ids") ?: JSONArray())
            .put("total_steps", s.totalSteps).put("step", s.currentStep))
    }

    private fun withSession(d: JSONObject, f: (LessonSession) -> Resp): Resp {
        val s = synchronized(sessions) { sessions[d.optString("session_id")] } ?: return Resp.error(404, "Session not found")
        return synchronized(s) { f(s) }
    }

    private fun sessionResponse(d: JSONObject, contentType: String?): Resp {
        if (contentType?.startsWith("multipart/") == true) return notOnDevice("Speech recognition")
        return withSession(d) { s ->
            val step = (d.opt("step") as? Number)?.toInt() ?: (d.opt("step") as? String)?.toIntOrNull()
                ?: return@withSession Resp.error(400, "step is required: the index of the step being answered")
            if (step !in 0 until s.totalSteps) return@withSession Resp.error(400, "step must be between 0 and ${s.totalSteps - 1}")
            val signal = s.checkResponse(d.optString("response", ""), step)
            Resp.json(JSONObject().put("signal", signal).put("message", signalMessages[signal]).put("step", step))
        }
    }

    private fun translateText(pack: Pack?, d: JSONObject): Resp {
        val text = d.optString("text", "")
        val direction = d.optString("direction", "hi-to-sat")
        if (direction !in directions) return Resp.error(400, "direction must be one of [hi-to-sat, sat-to-hi]")
        val t0 = System.nanoTime()
        val teacher = store.correction(text, direction)
        val fromPack = if (teacher == null) pack?.translation(text, direction) else null
        val (out, source) = when {
            teacher != null -> teacher to "teacher"
            fromPack != null -> fromPack.getString("text") to fromPack.getString("source")
            !engines.nmt -> return if (pack == null) noPack() else notOnDevice("Translation of new sentences")
            else -> return notOnDevice("Translation")
        }
        val t1 = System.nanoTime()
        val lang = if (direction == "hi-to-sat") "sat" else "hi"
        val audio = pack?.audioFile(out, lang)
        val t2 = System.nanoTime()
        fun sec(ns: Long) = Math.round(ns / 1e6) / 1000.0         // seconds, 3 decimals, as the hub rounds
        val lat = JSONObject().put("asr", 0.0).put("nmt", sec(t1 - t0)).put("tts", sec(t2 - t1)).put("total", sec(t2 - t0))
        val rid = UUID.randomUUID().toString().replace("-", "")
        store.logLatency(rid, JSONObject().put("direction", direction).put("input_type", "typed").put("source", source)
            .put("server_ms", (t2 - t0) / 1e6).put("tts_engine", if (audio != null) "pack" else "none"))
        synchronized(sessions) { sessions[d.optString("session_id")] }?.let {
            synchronized(it) { it.recordTranslation(if (direction == "hi-to-sat") text else out,
                                                    if (direction == "hi-to-sat") out else text, (t2 - t0) / 1e9) }
        }
        return Resp.json(JSONObject()
            .put("request_id", rid).put("translated_text", out).put("source", source)
            .put("model_score", JSONObject.NULL)
            .put("audio_url", audio?.let { "/audio/pack/${it.name}" } ?: JSONObject.NULL)
            .put("tts_error", if (audio == null) "No recorded audio for this line on the tablet yet (on-device speech: M2)" else JSONObject.NULL)
            .put("tts_engine", if (audio != null) "pack" else "none")
            .put("latency", lat).put("english_pivot", "").put("confidence", JSONObject.NULL))
    }

    private fun speak(pack: Pack?, d: JSONObject): Resp {
        val text = d.optString("text", "").trim()
        val lang = d.optString("lang", "sat")
        if (text.isEmpty() || lang !in setOf("sat", "hi")) return Resp.error(400, "text and lang (sat or hi) are required")
        val f = pack?.audioFile(text, lang) ?: return notOnDevice("Speech for new text")
        return Resp.json(JSONObject().put("audio_url", "/audio/pack/${f.name}").put("tts_error", JSONObject.NULL)
            .put("tts_engine", "pack"))
    }

    private fun packAudio(pack: Pack?, name: String): Resp {
        if (!name.matches(Regex("[0-9a-f]{40}\\.wav"))) return Resp.error(404, "Not found")
        val f = pack?.let { File(it.dir, "audio/$name") }?.takeIf { it.isFile } ?: return Resp.error(404, "Not found")
        return Resp.file(f, "audio/wav")
    }

    private fun feedback(d: JSONObject): Resp {
        val hindi = d.optString("hindi_text", ""); val santali = d.optString("santali_text", "")
        val direction = d.optString("direction", "hi-to-sat")
        if (direction !in directions) return Resp.error(400, "direction must be one of [hi-to-sat, sat-to-hi]")
        if (hindi.isEmpty() || santali.isEmpty()) return Resp.error(400, "Missing text")
        val corrected = d.optString("corrected_text", "").trim()
        val ok = d.optBoolean("is_correct", false)
        store.saveFeedback(hindi, santali, ok, corrected, direction)
        return Resp.json(JSONObject().put("status", "success").put("reused", corrected.isNotEmpty() || ok)
            .put("message", when {
                corrected.isNotEmpty() -> "Your correction will be reused for this sentence."
                ok -> "Saved. This translation will be reused."
                else -> "Saved."
            }))
    }

    private fun metricsClient(d: JSONObject): Resp {
        val total = d.opt("client_total_ms") as? Number
        val resp = d.opt("response_ms") as? Number
        if (total == null || resp == null) return Resp.error(400, "request_id, client_total_ms and response_ms are required")
        val last = d.opt("client_last_ms") as? Number
        val t = total.toDouble(); val r = resp.toDouble()
        if (!(r >= 0 && r <= t && t < 600_000) || (last != null && !(t <= last.toDouble() && last.toDouble() < 600_000)))
            return Resp.error(400, "timings out of range")
        if (!store.reportClientTiming(d.optString("request_id"), t, r, last?.toDouble())) return Resp.error(404, "unknown request_id")
        return Resp.json(JSONObject().put("status", "ok"))
    }

    private fun worksheet(pack: Pack?, d: JSONObject): Resp {
        pack ?: return noPack()
        val s = synchronized(sessions) { sessions[d.optString("session_id")] }
        val grade = s?.grade ?: d.opt("grade")?.toString() ?: ""
        val topic = s?.topic ?: d.optString("topic", "")
        val f = pack.worksheet(grade, topic) ?: return notOnDevice("Making a worksheet for this content")
        return Resp.file(f, "application/pdf")
    }
}
