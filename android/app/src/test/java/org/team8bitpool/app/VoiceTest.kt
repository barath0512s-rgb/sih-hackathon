package org.team8bitpool.app

import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import org.team8bitpool.app.core.Api
import org.team8bitpool.app.core.Audio
import org.team8bitpool.app.core.DeviceSettings
import org.team8bitpool.app.core.Multipart
import org.team8bitpool.app.core.Pack
import org.team8bitpool.app.core.SPOKEN_FEEDBACK_HI
import org.team8bitpool.app.core.Speech
import org.team8bitpool.app.core.Store
import java.io.ByteArrayOutputStream
import java.io.File
import java.security.MessageDigest

/** A1 on the tablet: the voice routes with a fake recogniser (the real one is JNI), and the audio helpers. */
class VoiceTest {
    @get:Rule val tmp = TemporaryFolder()
    private val packDir = File(Repo.root, "android/app/src/test/resources/pack")

    private class FakeSpeech(override val audioDir: File) : Speech {
        var next = ""
        val spoken = ArrayList<Pair<String, String>>()
        override fun transcribe(lang: String, samples16k: FloatArray) = next
        override fun speak(text: String, lang: String): File {
            spoken += text to lang
            val name = MessageDigest.getInstance("SHA-1").digest("$lang:$text".toByteArray()).joinToString("") { "%02x".format(it) }
            return File(audioDir, "$name.wav").also { it.writeBytes(Audio.wav(FloatArray(1600), 16000)) }
        }
        override fun describe() = JSONObject().put("asr", "fake").put("tts", "fake")
    }

    private fun setup(on: Boolean = true): Pair<Api, FakeSpeech> {
        val pack = Pack(packDir)
        val sp = FakeSpeech(tmp.newFolder("audio"))
        return Api({ pack }, Store(tmp.newFolder("store")), settings = DeviceSettings(onDeviceVoice = on), speechProvider = { sp }) to sp
    }

    private fun multipart(fields: Map<String, String>, wav: ByteArray): Pair<ByteArray, String> {
        val b = ByteArrayOutputStream(); val boundary = "XyZ123"
        b.write("--$boundary\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"recording.webm\"\r\nContent-Type: audio/wav\r\n\r\n".toByteArray())
        b.write(wav); b.write("\r\n".toByteArray())
        for ((k, v) in fields) b.write("--$boundary\r\nContent-Disposition: form-data; name=\"$k\"\r\n\r\n$v\r\n".toByteArray())
        b.write("--$boundary--\r\n".toByteArray())
        return b.toByteArray() to "multipart/form-data; boundary=$boundary"
    }

    private val wav = Audio.wav(FloatArray(16000) { (Math.sin(it / 10.0) * 0.3).toFloat() }, 16000)

    private fun stream(api: Api, direction: String): List<JSONObject> {
        val (body, ct) = multipart(mapOf("direction" to direction, "mode" to "lesson_script", "session_id" to ""), wav)
        val r = api.handle("POST", "/translate/audio_stream", emptyMap(), body, ct)
        assertEquals(200, r.status); assertEquals("application/x-ndjson", r.type)
        return String(r.body).trim().lines().map { JSONObject(it) }
    }

    @Test
    fun aSpokenLessonLineGetsThePacksTranslation() {
        val (api, sp) = setup()
        sp.next = "आज हम एक से दस तक गिनना सीखेंगे"            // ASR writes no danda
        val ev = stream(api, "hi-to-sat")
        assertEquals(listOf("asr", "chunk", "done"), ev.map { it.getString("type") })
        val chunk = ev[1]
        assertEquals("ᱛᱮᱦᱮᱸᱡ ᱟᱞᱮ ᱢᱤᱫ ᱠᱷᱚᱱ ᱜᱮᱞ ᱛᱩᱨᱩᱭ ᱜᱤᱱᱛᱤ ᱥᱮᱪᱮᱫᱟ।", chunk.getString("translated_text"))
        assertTrue(chunk.getJSONObject("match").getBoolean("matched"))
        assertTrue(chunk.getString("audio_url").startsWith("/audio/"))
        assertEquals(chunk.getString("translated_text"), ev[2].getString("translated_text"))
        // the audio it names can be fetched
        val url = chunk.getString("audio_url")
        assertEquals(200, api.handle("GET", url, emptyMap(), null, null).status)
    }

    @Test
    fun anythingElseIsNotALessonLineAndIsNeverTranslated() {
        val (api, sp) = setup()
        sp.next = "आज मौसम बहुत अच्छा है"
        val ev = stream(api, "hi-to-sat")
        val chunk = ev[1]
        assertEquals("not_a_lesson_line", chunk.getString("code"))
        assertEquals("", chunk.getString("translated_text"))
        assertTrue(chunk.isNull("audio_url"))
        assertEquals("आज मौसम बहुत अच्छा है", ev[0].getString("recognized_text"))
        assertTrue(sp.spoken.isEmpty())
    }

    @Test
    fun aSpokenSantaliAnswerIsGradedAndGetsHindiFeedback() {
        val (api, sp) = setup()
        val s = JSONObject(String(api.handle("POST", "/session/start", emptyMap(),
            JSONObject().put("grade", "1").put("topic", "counting_1_10").toString().toByteArray(), "application/json").body))
        sp.next = "ᱯᱮ"                                            // step 3 accepts ᱯᱮ (three)
        val (body, ct) = multipart(mapOf("session_id" to s.getString("session_id"), "step" to "3", "lang" to "sat"), wav)
        val r = JSONObject(String(api.handle("POST", "/session/response", emptyMap(), body, ct).body))
        assertEquals("green", r.getString("signal"))
        assertEquals("ᱯᱮ", r.getString("transcript"))
        assertEquals(SPOKEN_FEEDBACK_HI.getValue("green"), r.getString("feedback_hi"))
        assertTrue(r.getString("audio_url").startsWith("/audio/device/"))
        assertEquals(SPOKEN_FEEDBACK_HI.getValue("green") to "hi", sp.spoken.last())
    }

    @Test
    fun withTheFlagOffTheTabletStillRefusesSpeech() {
        val (api, sp) = setup(on = false)
        sp.next = "आज हम एक से दस तक गिनना सीखेंगे"
        val (body, ct) = multipart(mapOf("direction" to "hi-to-sat"), wav)
        val r = api.handle("POST", "/translate/audio_stream", emptyMap(), body, ct)
        assertEquals(503, r.status)
        assertEquals("engine_not_on_device", JSONObject(String(r.body)).getString("code"))
    }

    @Test
    fun flashcardSheetsComeFromThePack() {                    // A2
        val (api, _) = setup(on = false)
        val r = api.handle("GET", "/flashcards/pdf", mapOf("grade" to "2", "topic" to "addition"), null, null)
        assertEquals(200, r.status); assertEquals("application/pdf", r.type)
        assertEquals("%PDF", String(r.body, 0, 4))
        assertEquals(404, api.handle("GET", "/flashcards/pdf", mapOf("grade" to "9", "topic" to "none"), null, null).status)
        assertEquals(404, api.handle("GET", "/flashcards/pdf", mapOf("grade" to "2", "topic" to "../worksheets/2_addition"), null, null).status)
    }

    @Test
    fun wavRoundTripAndMultipart() {
        val x = FloatArray(320) { if (it % 2 == 0) 0.5f else -0.25f }
        val p = Audio.decodeWav(Audio.wav(x, 16000))!!
        assertEquals(16000, p.sampleRate); assertEquals(320, p.samples.size)
        assertEquals(0.5f, p.samples[0], 1e-3f); assertEquals(-0.25f, p.samples[1], 1e-3f)
        assertEquals(null, Audio.decodeWav("not a wav at all, long enough to pass the size check....".toByteArray()))
        val (body, ct) = multipart(mapOf("direction" to "sat-to-hi", "step" to "3"), wav)
        val parts = Multipart.parse(body, ct)
        assertArrayEquals(wav, parts.getValue("audio").data)
        assertEquals("sat-to-hi", parts.getValue("direction").text())
        assertEquals("recording.webm", parts.getValue("audio").filename)
    }

    @Test
    fun trimSilenceMatchesPython() {
        // indicconformer_asr.trim_silence on the same signal at sr=1000 keeps x[150:900] (750 samples)
        val x = FloatArray(1000) { if (it in 300 until 700) (0.5 * Math.sin(it.toDouble())).toFloat() else 0.001f }
        val y = Audio.trimSilence(x, sr = 1000)
        assertEquals(750, y.size)
        assertArrayEquals(x.copyOfRange(150, 900), y, 0f)
        val quiet = FloatArray(1000) { 0.001f }
        assertFalse(Audio.trimSilence(quiet, sr = 1000).size < 1000)     // all frames equal: kept
    }
}
