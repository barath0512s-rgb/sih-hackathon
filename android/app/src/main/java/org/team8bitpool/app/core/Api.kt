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
    private val settings: DeviceSettings = DeviceSettings(),
    private val speechProvider: () -> Speech? = { null },
    /** Where POST /sync/export writes the signed file (the app's shared folder); null in tests. */
    private val exportDir: File? = null,
) {
    /** On-device speech, when the flag is on and a model pack is installed (A1). */
    private fun speech(): Speech? = if (settings.onDeviceVoice) speechProvider() else null
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
            "GET /flashcards/pdf" -> pack?.flashcardsPdf(query["grade"] ?: "", query["topic"] ?: "")
                ?.let { Resp.file(it, "application/pdf") } ?: Resp.error(404, "No flashcard sheet for that lesson on the tablet")
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
            "POST /session/response" -> sessionResponse(json, body, contentType)
            "POST /session/summary" -> withSession(json) { s -> Resp.json(s.summary()) }
            "POST /translate/text" -> translateText(pack, json)
            "POST /translate/audio", "POST /translate/audio_stream" -> translateAudio(pack, body, contentType, path.endsWith("_stream"))
            "POST /speak" -> speak(pack, json)
            "POST /feedback" -> feedback(json)
            "POST /metrics/client" -> metricsClient(json)
            "POST /worksheet" -> worksheet(pack, json)
            "POST /sync/export" -> syncExport()
            "GET /progress/lakshya" -> progressLakshya(query["format"] ?: "json")
            "GET /orf/passages" -> Resp.json(pack?.orfPassages ?: JSONObject().put("passages", JSONArray()))
            "POST /orf/score" -> orfScore(pack, body, contentType)
            "POST /sync/import" -> Resp.error(501, "Tablet files are merged on the hub", "hub_only")
            "POST /curriculum/import", "POST /curriculum/save", "POST /curriculum/photo" ->
                Resp.error(501, "Lessons are written on the hub and arrive in the content pack", "hub_only")
            else -> when {
                method == "GET" && path.startsWith("/audio/pack/") -> packAudio(pack, path.removePrefix("/audio/pack/"))
                method == "GET" && path.startsWith("/audio/device/") -> deviceAudio(path.removePrefix("/audio/device/"))
                else -> Resp.error(404, "Not found")
            }
        }
    }

    private fun healthModels(pack: Pack?): JSONObject {
        val sp = speech()
        fun lang(tts: String) = JSONObject()
            .put("asr", JSONObject().put("engine", if (sp != null) "on device: " + sp.describe().optString("asr")
                else if (engines.asr) "on device" else "not on device yet (M3)"))
            .put("nmt", JSONObject().put("engine", if (engines.nmt) "on device"
                else "not on device yet (M4); lesson lines come from the content pack" +
                    (if (sp != null) " (spoken lesson lines are matched to them)" else "")))
            .put("tts", JSONObject().put("engine", if (sp != null) "on device: " + sp.describe().optString("tts")
                else if (engines.tts) "on device" else "not on device yet (M2); $tts audio comes from the content pack"))
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

    private fun sessionResponse(d0: JSONObject, body: ByteArray?, contentType: String?): Resp {
        var d = d0
        var transcript: String? = null
        if (contentType?.startsWith("multipart/") == true) {
            val sp = speech() ?: return notOnDevice("Speech recognition")
            val parts = Multipart.parse(body ?: ByteArray(0), contentType)
            val audio = parts["audio"] ?: return Resp.error(400, "No audio")
            val pcm = Audio.decodeWav(audio.data) ?: return Resp.error(415, "The tablet reads WAV recordings only", "audio_format")
            val lang = parts["lang"]?.text() ?: "sat"
            if (lang !in setOf("sat", "hi")) return Resp.error(400, "lang must be sat or hi")
            transcript = sp.transcribe(lang, Audio.to16k(pcm))
            d = JSONObject().put("session_id", parts["session_id"]?.text() ?: "").put("step", parts["step"]?.text() ?: "")
                .put("response", transcript)
        }
        return withSession(d) { s ->
            val step = (d.opt("step") as? Number)?.toInt() ?: (d.opt("step") as? String)?.toIntOrNull()
                ?: return@withSession Resp.error(400, "step is required: the index of the step being answered")
            if (step !in 0 until s.totalSteps) return@withSession Resp.error(400, "step must be between 0 and ${s.totalSteps - 1}")
            val signal = s.checkResponse(d.optString("response", ""), step)
            taught(s)
            store.logAnswer(s.grade, s.topic, s.lesson.optJSONArray("lakshya_ids") ?: JSONArray(), signal)
            val out = JSONObject().put("signal", signal).put("message", signalMessages[signal]).put("step", step)
            if (transcript != null) {
                out.put("transcript", transcript)
                // A1: the Hindi feedback for the child, spoken on the tablet
                val hi = SPOKEN_FEEDBACK_HI.getValue(signal)
                val f = runCatching { speech()?.speak(hi, "hi") }.getOrNull()
                out.put("feedback_hi", hi).put("audio_url", f?.let { "/audio/device/${it.name}" } ?: JSONObject.NULL)
            }
            Resp.json(out)
        }
    }

    /**
     * A1: a spoken lesson line, recognised on the tablet and matched to the pack's
     * pre-translated lines (LessonMatch). Answers like the hub: JSON for
     * /translate/audio, NDJSON events (asr, chunk, done) for /translate/audio_stream.
     * Below the threshold: the transcript and code "not_a_lesson_line", no translation.
     */
    private fun translateAudio(pack: Pack?, body: ByteArray?, contentType: String?, stream: Boolean): Resp {
        val sp = speech() ?: return notOnDevice("Speech recognition")
        pack ?: return noPack()
        if (contentType?.startsWith("multipart/") != true) return Resp.error(400, "No audio")
        val parts = Multipart.parse(body ?: ByteArray(0), contentType)
        val audio = parts["audio"] ?: return Resp.error(400, "No audio")
        val direction = parts["direction"]?.text() ?: "hi-to-sat"
        if (direction !in directions) return Resp.error(400, "direction must be one of [hi-to-sat, sat-to-hi]")
        val pcm = Audio.decodeWav(audio.data) ?: return Resp.error(415, "The tablet reads WAV recordings only", "audio_format")
        val inLang = if (direction == "hi-to-sat") "hi" else "sat"
        val outLang = if (direction == "hi-to-sat") "sat" else "hi"
        val t0 = System.nanoTime()
        val recognized = sp.transcribe(inLang, Audio.to16k(pcm))
        val t1 = System.nanoTime()
        val lines = pack.lines(direction)
        val thr = settings.threshold[inLang] ?: 1.0
        val m = LessonMatch.match(recognized, lines.keys, thr, inLang)
        val entry = if (m.matched) lines.getValue(m.line!!) else null
        val teacher = if (m.matched) store.correction(m.line!!, direction) else null
        // A5: free-form speech only where recognition and translation both fit in memory (settings.freeFormVoice)
        val free = if (teacher == null && entry == null && settings.freeFormVoice) runCatching { sp.translate(recognized, direction) }.getOrNull() else null
        val out = teacher ?: entry?.getString("text") ?: free?.text
        val source = when { teacher != null -> "teacher"; entry != null -> entry.optString("source", "pack"); free != null -> "model"; else -> "none" }
        val t2 = System.nanoTime()
        var engine = "none"
        var audioUrl: String? = null
        if (out != null) {
            val pf = pack.audioFile(out, outLang)
            if (pf != null) { audioUrl = "/audio/pack/${pf.name}"; engine = "pack" }
            else runCatching { sp.speak(out, outLang) }.getOrNull()?.let { audioUrl = "/audio/device/${it.name}"; engine = "device" }
        }
        val t3 = System.nanoTime()
        fun sec(ns: Long) = Math.round(ns / 1e6) / 1000.0
        val lat = JSONObject().put("asr", sec(t1 - t0)).put("nmt", sec(t2 - t1)).put("tts", sec(t3 - t2)).put("total", sec(t3 - t0))
        val rid = UUID.randomUUID().toString().replace("-", "")
        store.logLatency(rid, JSONObject().put("direction", direction).put("input_type", "voice").put("source", source)
            .put("server_ms", (t3 - t0) / 1e6).put("tts_engine", engine).put("match_score", m.score).put("matched", m.matched))
        val match = JSONObject().put("line", m.line ?: JSONObject.NULL).put("score", Math.round(m.score * 1000) / 1000.0)
            .put("threshold", thr).put("matched", m.matched)
        val ttsError: Any = when {
            out == null -> "Not a lesson line: use the laptop hub or type"
            audioUrl == null -> "No audio for this line on the tablet"
            else -> JSONObject.NULL
        }
        val chunk = JSONObject().put("type", "chunk").put("i", 0).put("source_text", recognized)
            .put("translated_text", out ?: "").put("source", source).put("audio_url", audioUrl ?: JSONObject.NULL)
            .put("tts_error", ttsError).put("tts_engine", engine).put("ms", (t3 - t0) / 1_000_000)
            .put("needs_review", teacher == null && (entry?.optBoolean("needs_review") == true || free?.needsReview == true))
            .put("nearest_verified", JSONObject.NULL).put("match", match)
            .put("review_status", entry?.optString("review_status") ?: JSONObject.NULL)
        if (out == null) chunk.put("code", "not_a_lesson_line")
        if (out != null) synchronized(sessions) { sessions[parts["session_id"]?.text() ?: ""] }?.let {
            taught(it); synchronized(it) { it.recordTranslation(if (direction == "hi-to-sat") recognized else out,
                                                    if (direction == "hi-to-sat") out else recognized, (t3 - t0) / 1e9) }
        }
        if (!stream) {
            val j = JSONObject(chunk.toString()); j.remove("type"); j.remove("i")
            return Resp.json(j.put("request_id", rid).put("recognized_text", recognized).put("latency", lat)
                .put("model_score", JSONObject.NULL).put("english_pivot", "").put("confidence", JSONObject.NULL))
        }
        val events = listOf(
            JSONObject().put("type", "asr").put("recognized_text", recognized).put("chunks", 1),
            chunk,
            JSONObject().put("type", "done").put("request_id", rid).put("translated_text", out ?: "")
                .put("source", source).put("latency", lat))
        return Resp(200, "application/x-ndjson", events.joinToString("") { it.toString() + "\n" }.toByteArray())
    }

    /** A lesson counts as taught (A8) once something happens in it: the page opens a
     *  session on start, which alone is not teaching. */
    private val counted = HashSet<String>()
    private fun taught(s: LessonSession) {
        if (synchronized(counted) { counted.add(s.sid) })
            store.logSession(s.grade, s.topic, s.lesson.optJSONArray("lakshya_ids") ?: JSONArray())
    }

    /** A8: this tablet's class counts per Lakshya and ISO week (json or csv; the PDF is made on the hub). */
    private fun progressLakshya(format: String): Resp {
        val agg = LinkedHashMap<String, JSONObject>()
        for (r in store.classCounts()) {
            val d = java.time.LocalDate.parse(r.getString("day"))
            val week = "%d-W%02d".format(d.get(java.time.temporal.IsoFields.WEEK_BASED_YEAR),
                                         d.get(java.time.temporal.IsoFields.WEEK_OF_WEEK_BASED_YEAR))
            val lids = r.optJSONArray("lakshya_ids") ?: JSONArray()
            for (i in 0 until lids.length()) {
                val a = agg.getOrPut("$week|${lids.getString(i)}") {
                    JSONObject().put("lakshya_id", lids.getString(i)).put("week", week).put("lessons_taught", 0)
                        .put("green", 0).put("yellow", 0).put("red", 0).put("sources", JSONArray().put("tablet:${store.deviceId}"))
                }
                a.put("lessons_taught", a.getInt("lessons_taught") + r.getInt("sessions"))
                for (k in listOf("green", "yellow", "red")) a.put(k, a.getInt(k) + r.getInt(k))
            }
        }
        val rows = agg.values.sortedWith(compareBy({ it.getString("week") }, { it.getString("lakshya_id") }))
        for (a in rows) {
            val n = a.getInt("green") + a.getInt("yellow") + a.getInt("red")
            a.put("green_share", if (n > 0) Math.round(a.getInt("green") * 1000.0 / n) / 1000.0 else JSONObject.NULL)
        }
        return when (format) {
            "csv" -> Resp(200, "text/csv", (listOf("week,lakshya_id,lessons_taught,green,yellow,red,green_share,sources") +
                rows.map { a -> listOf(a.getString("week"), a.getString("lakshya_id"), a.getInt("lessons_taught"), a.getInt("green"),
                    a.getInt("yellow"), a.getInt("red"), if (a.isNull("green_share")) "" else a.getDouble("green_share"),
                    "tablet:${store.deviceId}").joinToString(",") }).joinToString("\n", postfix = "\n").toByteArray())
            "json" -> Resp.json(JSONObject().put("rows", JSONArray(rows)))
            else -> Resp.error(404, "The progress PDF is made on the hub; the tablet gives csv", "hub_only")
        }
    }

    /** C1: a child's reading, recognised on the tablet; the recording is never written. */
    private fun orfScore(pack: Pack?, body: ByteArray?, contentType: String?): Resp {
        val sp = speech() ?: return notOnDevice("Speech recognition")
        pack ?: return noPack()
        if (contentType?.startsWith("multipart/") != true) return Resp.error(400, "No audio")
        val parts = Multipart.parse(body ?: ByteArray(0), contentType)
        if (parts["consent"]?.text() != "1") return Resp.error(400, "The teacher must confirm consent first", "consent_required")
        val audio = parts["audio"] ?: return Resp.error(400, "No audio")
        val passages = pack.orfPassages.getJSONArray("passages")
        val id = parts["passage_id"]?.text() ?: ""
        val p = (0 until passages.length()).map { passages.getJSONObject(it) }.firstOrNull { it.getString("id") == id }
            ?: return Resp.error(404, "Unknown passage")
        val pcm = Audio.decodeWav(audio.data) ?: return Resp.error(415, "The tablet reads WAV recordings only", "audio_format")
        val x = Audio.to16k(pcm)
        val spoken = sp.transcribe("hi", x)
        val seconds = Audio.trimSilence(x).size / 16000.0
        val s = Orf.score(p.getString("text"), spoken, seconds)
        val wcpm = if (s.isNull("wcpm")) null else s.getDouble("wcpm")
        return Resp.json(s.put("passage_id", id).put("grade", p.getString("grade")).put("transcript", spoken)
            .put("nipun", Orf.nipunBand(p.getString("grade"), wcpm) ?: JSONObject.NULL))
    }

    /** A4: the signed corrections-and-counts file for the hub. */
    private fun syncExport(): Resp {
        val bytes = store.exportSigned()
        val name = "nijbhasha-export-${store.deviceId}-${System.currentTimeMillis() / 1000}.json"
        val saved = exportDir?.let { d -> d.mkdirs(); File(d, name).also { it.writeBytes(bytes) } }
        val p = JSONObject(JSONObject(String(bytes, Charsets.UTF_8)).getString("payload"))
        return Resp.json(JSONObject().put("device_id", store.deviceId).put("file", name)
            .put("saved_to", saved?.path ?: JSONObject.NULL)
            .put("corrections", p.getJSONArray("corrections").length()).put("class_rows", p.getJSONArray("analytics").length())
            .put("export", JSONObject(String(bytes, Charsets.UTF_8))))
    }

    private fun deviceAudio(name: String): Resp {
        if (!name.matches(Regex("[0-9a-f]{40}\\.wav"))) return Resp.error(404, "Not found")
        val f = speechProvider()?.audioDir?.let { File(it, name) }?.takeIf { it.isFile } ?: return Resp.error(404, "Not found")
        return Resp.file(f, "audio/wav")
    }

    private fun translateText(pack: Pack?, d: JSONObject): Resp {
        val text = d.optString("text", "")
        val direction = d.optString("direction", "hi-to-sat")
        if (direction !in directions) return Resp.error(400, "direction must be one of [hi-to-sat, sat-to-hi]")
        val t0 = System.nanoTime()
        val teacher = store.correction(text, direction)
        val fromPack = if (teacher == null) pack?.translation(text, direction) else null
        var deviceModel: Translation? = null
        val (out, source) = when {
            teacher != null -> teacher to "teacher"
            fromPack != null -> fromPack.getString("text") to fromPack.getString("source")
            else -> {
                val tr = runCatching { speech()?.translate(text, direction) }.getOrNull()
                    ?: return if (pack == null) noPack() else notOnDevice("Translation of new sentences")
                deviceModel = tr
                tr.text to "model"
            }
        }
        val t1 = System.nanoTime()
        val lang = if (direction == "hi-to-sat") "sat" else "hi"
        val packAudio = pack?.audioFile(out, lang)
        val deviceAudio = if (packAudio == null && deviceModel != null) runCatching { speech()?.speak(out, lang) }.getOrNull() else null
        val audioUrl = packAudio?.let { "/audio/pack/${it.name}" } ?: deviceAudio?.let { "/audio/device/${it.name}" }
        val engine = if (packAudio != null) "pack" else if (deviceAudio != null) "device" else "none"
        val t2 = System.nanoTime()
        fun sec(ns: Long) = Math.round(ns / 1e6) / 1000.0         // seconds, 3 decimals, as the hub rounds
        val lat = JSONObject().put("asr", 0.0).put("nmt", sec(t1 - t0)).put("tts", sec(t2 - t1)).put("total", sec(t2 - t0))
        val rid = UUID.randomUUID().toString().replace("-", "")
        store.logLatency(rid, JSONObject().put("direction", direction).put("input_type", "typed").put("source", source)
            .put("server_ms", (t2 - t0) / 1e6).put("tts_engine", engine))
        synchronized(sessions) { sessions[d.optString("session_id")] }?.let {
            taught(it); synchronized(it) { it.recordTranslation(if (direction == "hi-to-sat") text else out,
                                                    if (direction == "hi-to-sat") out else text, (t2 - t0) / 1e9) }
        }
        return Resp.json(JSONObject()
            .put("request_id", rid).put("translated_text", out).put("source", source)
            .put("model_score", JSONObject.NULL)
            .put("audio_url", audioUrl ?: JSONObject.NULL)
            .put("tts_error", if (audioUrl == null) "No recorded audio for this line on the tablet yet (on-device speech: M2)" else JSONObject.NULL)
            .put("tts_engine", engine)
            .put("latency", lat).put("english_pivot", "").put("confidence", JSONObject.NULL)
            // A3: a pack line the round-trip check flagged (a teacher's correction clears it)
            .put("needs_review", source != "teacher" && (fromPack?.optBoolean("needs_review") == true || deviceModel?.needsReview == true)))
    }

    private fun speak(pack: Pack?, d: JSONObject): Resp {
        val text = d.optString("text", "").trim()
        val lang = d.optString("lang", "sat")
        if (text.isEmpty() || lang !in setOf("sat", "hi")) return Resp.error(400, "text and lang (sat or hi) are required")
        pack?.audioFile(text, lang)?.let { f ->
            return Resp.json(JSONObject().put("audio_url", "/audio/pack/${f.name}").put("tts_error", JSONObject.NULL)
                .put("tts_engine", "pack"))
        }
        val f = runCatching { speech()?.speak(text, lang) }.getOrNull() ?: return notOnDevice("Speech for new text")
        return Resp.json(JSONObject().put("audio_url", "/audio/device/${f.name}").put("tts_error", JSONObject.NULL)
            .put("tts_engine", "device"))
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
