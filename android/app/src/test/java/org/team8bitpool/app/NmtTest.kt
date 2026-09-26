package org.team8bitpool.app

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.team8bitpool.app.core.IndicProc
import org.team8bitpool.app.core.NmtGuard
import org.team8bitpool.app.core.NmtTokenizer
import org.team8bitpool.app.core.OnnxNmt
import org.team8bitpool.app.core.Spm
import java.io.File

/**
 * A5 golden test: the tablet's translation port against the app's Python path on the
 * 300 sentences of nmt_vectors.json (tools/android/make_nmt_vectors.py). Needs the
 * model files (models/indictrans2-*, not in git): skipped without them (CI).
 * Writes build/nmt_golden.json (the rates) for bench/results.
 */
class NmtTest {
    private val v = JSONObject(File(Repo.root, "android/app/src/test/resources/nmt_vectors.json").readText()).getJSONArray("cases")
    private val tokDir = File(Repo.root, "models/indictrans2-indic-indic")
    private val onnxDir = File(Repo.root, "models/indictrans2-onnx")

    private fun cases() = (0 until v.length()).map { v.getJSONObject(it) }
    private fun langs(c: JSONObject) = if (c.getString("direction") == "hi-to-sat") "hin_Deva" to "sat_Olck" else "sat_Olck" to "hin_Deva"

    @Test
    fun preprocessingMatchesPython() {
        val bad = cases().filter { c -> val (s, t) = langs(c); IndicProc.preprocess(c.getString("src"), s, t).text != c.getString("pre") }
        bad.take(5).forEach { println("PRE MISMATCH ${it.getString("src")}\n  py: ${it.getString("pre")}\n  kt: ${IndicProc.preprocess(it.getString("src"), langs(it).first, langs(it).second).text}") }
        assertTrue("${bad.size} of ${v.length()} preprocessed differently", bad.isEmpty())
    }

    @Test
    fun tokenIdsMatchPython() {
        assumeTrue("model files not present", File(tokDir, "model.SRC").isFile)
        val tok = NmtTokenizer(Spm.load(File(tokDir, "model.SRC")), NmtTokenizer.dict(File(tokDir, "dict.SRC.json")),
                               NmtTokenizer.dict(File(tokDir, "dict.TGT.json")))
        var same = 0
        for (c in cases()) {
            val want = c.getJSONArray("ids").let { a -> IntArray(a.length()) { a.getInt(it) } }
            val got = tok.encode(c.getString("pre"))
            if (want.contentEquals(got)) same++
            else println("IDS MISMATCH ${c.getString("pre")}\n  py: ${c.getJSONArray("pieces")}\n  kt: ${tok.pieces(c.getString("pre"))}")
        }
        val rate = same.toDouble() / v.length()
        File(Repo.root, "android/app/build").mkdirs()
        File(Repo.root, "android/app/build/nmt_golden_ids.json").writeText(JSONObject().put("same", same).put("n", v.length()).toString())
        assertTrue("identical token ids on $same of ${v.length()} (the bar is 98 %)", rate >= 0.98)
    }

    @Test
    fun postprocessingMatchesPython() {
        assumeTrue("model files not present", File(tokDir, "dict.TGT.json").isFile)
        val tok = NmtTokenizer(Spm.load(File(tokDir, "model.SRC")), NmtTokenizer.dict(File(tokDir, "dict.SRC.json")),
                               NmtTokenizer.dict(File(tokDir, "dict.TGT.json")))
        var n = 0
        for (c in cases().filter { it.has("seq") }) {
            val (s, t) = langs(c)
            val seq = c.getJSONArray("seq").let { a -> (0 until a.length()).map { a.getInt(it) } }
            assertEquals(c.getString("decoded"), tok.decode(seq))
            val pre = IndicProc.preprocess(c.getString("src"), s, t)
            val out = NmtGuard.cutStemLoop(IndicProc.postprocess(tok.decode(seq), t, pre.placeholders)).first
            assertEquals("post ${c.getString("src")}", c.getString("out"), out)
            n++
        }
        assertEquals(80, n)
    }

    @Test
    fun endToEndMatchesThePythonEngine() {
        assumeTrue("ONNX files not present", File(onnxDir, "encoder.int8.onnx").isFile)
        // The desktop ONNX Runtime does not load on every Windows machine (a DLL clash with the
        // system's own onnxruntime.dll); the same check runs on the device (tools/android/nmt_bench.py).
        val nmt0 = try { OnnxNmt(onnxDir, tokDir, threads = 4) } catch (e: Throwable) {
            assumeTrue("desktop ONNX Runtime unavailable here: ${e.message}", false); return
        }
        nmt0.use { nmt ->
            var sameSeq = 0; var sameOut = 0; var n = 0
            for (c in cases().filter { it.has("seq") }) {
                val (s, t) = langs(c)
                val out = nmt.translate(c.getString("src"), s, t)
                val want = c.getJSONArray("seq").let { a -> (0 until a.length()).map { a.getInt(it) } }
                if (nmt.lastSeq == want) sameSeq++ else println("SEQ DIFF ${c.getString("src")}\n  py: ${c.getString("out")}\n  kt: $out")
                if (out == c.getString("out")) sameOut++
                n++
            }
            File(Repo.root, "android/app/build/nmt_golden_e2e.json").writeText(
                JSONObject().put("same_seq", sameSeq).put("same_out", sameOut).put("n", n).toString())
            assertTrue("identical output on $sameOut of $n", sameOut.toDouble() / n >= 0.95)
        }
    }
}
