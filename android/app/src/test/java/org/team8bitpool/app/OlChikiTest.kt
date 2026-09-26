package org.team8bitpool.app

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test
import org.team8bitpool.app.core.OlChiki
import java.io.File

/** OlChiki.kt must pass every vector translit/olchiki.py passes (tests/data/olchiki_vectors.json). */
class OlChikiTest {
    @Test
    fun everyVectorMatchesPython() {
        val v = JSONObject(File(Repo.root, "tests/data/olchiki_vectors.json").readText()).getJSONArray("vectors")
        var n = 0
        for (i in 0 until v.length()) {
            val c = v.getJSONObject(i)
            val got = when (c.getString("function")) {
                "to_devanagari" -> OlChiki.toDevanagari(c.getString("input"), c.getString("digits"))
                "to_latin" -> OlChiki.toLatin(c.getString("input"), c.getString("digits"))
                else -> error("unknown function ${c.getString("function")}")
            }
            assertEquals("vector ${c.getInt("id")} (${c.optString("rule")}) ${c.getString("input")}", c.getString("expected"), got)
            n++
        }
        assertEquals(v.length(), n)
    }
}
