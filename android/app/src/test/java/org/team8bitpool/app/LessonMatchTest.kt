package org.team8bitpool.app

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test
import org.team8bitpool.app.core.LessonMatch
import java.io.File

/** LessonMatch.kt must agree with lesson_match.py (tests/data/lesson_match_vectors.json). */
class LessonMatchTest {
    private val v = JSONObject(File(Repo.root, "tests/data/lesson_match_vectors.json").readText())
    private fun cands(lang: String): List<String> {
        val a = v.getJSONObject("candidates").getJSONArray(lang)
        return (0 until a.length()).map { a.getString(it) }
    }

    @Test
    fun canonicalMatchesPython() {
        val a = v.getJSONArray("canonical")
        for (i in 0 until a.length()) {
            val c = a.getJSONObject(i)
            assertEquals("#$i ${c.getString("in")}", c.getString("out"), LessonMatch.canonical(c.getString("in"), c.getString("lang")))
        }
    }

    @Test
    fun similarityMatchesPython() {
        val a = v.getJSONArray("similarity")
        for (i in 0 until a.length()) {
            val c = a.getJSONObject(i)
            assertEquals("#$i", c.getDouble("score"), LessonMatch.similarity(c.getString("a"), c.getString("b"), c.getString("lang")), 1e-6)
        }
    }

    @Test
    fun bestLineAndDecisionMatchPython() {
        val a = v.getJSONArray("match")
        for (i in 0 until a.length()) {
            val c = a.getJSONObject(i)
            val lang = c.getString("lang")
            val r = LessonMatch.match(c.getString("in"), cands(lang), c.getDouble("threshold"), lang)
            assertEquals("#$i line ${c.getString("in")}", if (c.isNull("line")) null else c.getString("line"), r.line)
            assertEquals("#$i score", c.getDouble("score"), r.score, 1e-6)
            assertEquals("#$i matched", c.getBoolean("matched"), r.matched)
            assertEquals("#$i numbers", c.getBoolean("numbers_agree"), r.numbersAgree)
        }
    }
}
