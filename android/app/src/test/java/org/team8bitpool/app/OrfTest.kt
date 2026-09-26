package org.team8bitpool.app

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test
import org.team8bitpool.app.core.Orf
import java.io.File

/** Orf.kt must score readings as orf.py does (tests/data/orf_vectors.json). */
class OrfTest {
    @Test
    fun scoresMatchPython() {
        val a = JSONObject(File(Repo.root, "tests/data/orf_vectors.json").readText()).getJSONArray("cases")
        for (i in 0 until a.length()) {
            val c = a.getJSONObject(i)
            val s = Orf.score(c.getString("passage"), c.getString("spoken"), c.getDouble("seconds"))
            val st = s.getJSONArray("words").let { w -> (0 until w.length()).map { w.getJSONObject(it).getString("status") } }
            val want = c.getJSONArray("statuses").let { w -> (0 until w.length()).map { w.getString(it) } }
            assertEquals("#$i statuses", want, st)
            for (k in listOf("correct", "errors", "attempted")) assertEquals("#$i $k", c.getInt(k), s.getInt(k))
            if (!c.isNull("wcpm")) assertEquals("#$i wcpm", c.getDouble("wcpm"), s.getDouble("wcpm"), 0.051)
            val band = Orf.nipunBand(c.getString("grade"), if (s.isNull("wcpm")) null else s.getDouble("wcpm"))
            if (c.isNull("nipun")) assertEquals(null, band) else assertEquals(c.getJSONObject("nipun").getBoolean("met"), band!!.getBoolean("met"))
        }
    }
}
