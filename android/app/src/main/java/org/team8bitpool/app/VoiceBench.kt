package org.team8bitpool.app

import android.content.Context
import android.os.Debug
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import org.team8bitpool.app.core.Api
import java.io.ByteArrayOutputStream
import java.io.File
import kotlin.concurrent.thread

/**
 * Debug builds only (MainActivity.debugImport): the A1 on-device benchmark, run by
 * tools/android/voice_bench.py. Clips pushed by adb into the app's external
 * files/bench/ folder go through the same Api routes the page uses:
 *   clips[]   -> POST /translate/audio (recognise, match, pack audio or synthesis)
 *   answers[] -> POST /session/start, then a spoken answer to POST /session/response
 *   tts[]     -> POST /speak for lines with no pack audio (on-device synthesis)
 *   texts[]   -> POST /translate/text for sentences not in the pack (A5: translated on the tablet)
 * Times are measured around each call (from the WAV handed over to the reply with
 * its audio file ready; the WebView's playback start is not included). App-process
 * PSS is sampled after each call. Result: files/bench/result.json.
 */
object VoiceBench {
    private const val TAG = "tablet"

    fun run(ctx: Context, api: Api, manifestName: String) = thread(name = "voice-bench") {
        val dir = ctx.getExternalFilesDir("bench") ?: return@thread
        val man = JSONObject(File(dir, manifestName).readText())
        val out = JSONObject().put("device", android.os.Build.MODEL).put("android", android.os.Build.VERSION.RELEASE)
        var peakPss = 0L
        fun pss() { peakPss = maxOf(peakPss, Debug.getPss()) }
        fun post(path: String, parts: List<Triple<String, String?, ByteArray>>): Pair<JSONObject, Double> {
            val boundary = "bench" + System.nanoTime()
            val b = ByteArrayOutputStream()
            for ((name, filename, data) in parts) {
                b.write("--$boundary\r\nContent-Disposition: form-data; name=\"$name\"".toByteArray())
                if (filename != null) b.write("; filename=\"$filename\"\r\nContent-Type: audio/wav".toByteArray())
                b.write("\r\n\r\n".toByteArray()); b.write(data); b.write("\r\n".toByteArray())
            }
            b.write("--$boundary--\r\n".toByteArray())
            val t0 = System.nanoTime()
            val r = api.handle("POST", path, emptyMap(), b.toByteArray(), "multipart/form-data; boundary=$boundary")
            val ms = (System.nanoTime() - t0) / 1e6
            pss()
            return JSONObject(String(r.body)).put("_status", r.status) to ms
        }
        fun postJson(path: String, j: JSONObject) =
            JSONObject(String(api.handle("POST", path, emptyMap(), j.toString().toByteArray(), "application/json").body))

        pss()
        val clips = JSONArray()
        val ca = man.optJSONArray("clips") ?: JSONArray()
        for (i in 0 until ca.length()) {
            val c = ca.getJSONObject(i)
            val wav = File(dir, c.getString("file")).readBytes()
            val dirn = if (c.getString("lang") == "hi") "hi-to-sat" else "sat-to-hi"
            val (r, ms) = post("/translate/audio", listOf(Triple("audio", "a.wav", wav), Triple("direction", null, dirn.toByteArray())))
            clips.put(JSONObject().put("id", c.getString("id")).put("ms", ms).put("recognized_text", r.optString("recognized_text"))
                .put("match", r.optJSONObject("match")).put("audio_url", r.opt("audio_url")).put("tts_engine", r.optString("tts_engine"))
                .put("latency", r.optJSONObject("latency")).put("status", r.optInt("_status")))
            if (i % 25 == 0) Log.i(TAG, "voice_bench clips $i/${ca.length()}")
        }
        out.put("clips", clips)

        val answers = JSONArray()
        val aa = man.optJSONArray("answers") ?: JSONArray()
        for (i in 0 until aa.length()) {
            val a = aa.getJSONObject(i)
            val s = postJson("/session/start", JSONObject().put("grade", a.getString("grade")).put("topic", a.getString("topic")))
            val sid = s.optString("session_id")
            val (r, ms) = post("/session/response", listOf(Triple("audio", "a.wav", File(dir, a.getString("file")).readBytes()),
                Triple("session_id", null, sid.toByteArray()), Triple("step", null, a.getInt("step").toString().toByteArray()),
                Triple("lang", null, "sat".toByteArray())))
            answers.put(JSONObject().put("id", a.getString("id")).put("ms", ms).put("expect", a.getString("expect"))
                .put("signal", r.optString("signal")).put("transcript", r.optString("transcript"))
                .put("feedback_hi", r.optString("feedback_hi")).put("audio_url", r.opt("audio_url")).put("status", r.optInt("_status")))
        }
        out.put("answers", answers)

        val tts = JSONArray()
        val ta = man.optJSONArray("tts") ?: JSONArray()
        for (i in 0 until ta.length()) {
            val t = ta.getJSONObject(i)
            val t0 = System.nanoTime()
            val r = JSONObject(String(api.handle("POST", "/speak", emptyMap(),
                JSONObject().put("text", t.getString("text")).put("lang", t.getString("lang")).toString().toByteArray(), "application/json").body))
            tts.put(JSONObject().put("text", t.getString("text")).put("lang", t.getString("lang"))
                .put("ms", (System.nanoTime() - t0) / 1e6).put("tts_engine", r.optString("tts_engine")).put("audio_url", r.opt("audio_url")))
            pss()
        }
        out.put("tts", tts)

        // A5: typed sentences (not in the pack: translated on the tablet)
        val texts = JSONArray()
        val xa = man.optJSONArray("texts") ?: JSONArray()
        for (i in 0 until xa.length()) {
            val x = xa.getJSONObject(i)
            val t0 = System.nanoTime()
            val r = JSONObject(String(api.handle("POST", "/translate/text", emptyMap(),
                JSONObject().put("text", x.getString("text")).put("direction", x.getString("direction")).toString().toByteArray(), "application/json").body))
            texts.put(JSONObject().put("id", x.getString("id")).put("ms", (System.nanoTime() - t0) / 1e6)
                .put("translated_text", r.optString("translated_text")).put("source", r.optString("source"))
                .put("needs_review", r.optBoolean("needs_review")).put("latency", r.optJSONObject("latency")))
            pss()
            if (i % 50 == 0) Log.i(TAG, "voice_bench texts $i/${xa.length()}")
        }
        out.put("texts", texts).put("peak_app_pss_kb", peakPss)
        File(dir, "result.json").writeText(out.toString())
        Log.i(TAG, "voice_bench done: ${clips.length()} clips, ${answers.length()} answers, ${tts.length()} tts, peak PSS $peakPss kB")
    }
}
