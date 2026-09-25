package org.team8bitpool.app

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test
import org.team8bitpool.app.core.TextNorm
import org.team8bitpool.app.core.gradeAnswer
import java.io.File

/** The Kotlin ports must agree with Python on every vector (tests/data/normalize_key_vectors.json). */
class TextNormTest {
    private val vectors = JSONObject(File(Repo.root, "tests/data/normalize_key_vectors.json").readText())

    @Test
    fun normalizeKeyMatchesPython() {
        val v = vectors.getJSONArray("normalize_key")
        for (i in 0 until v.length()) {
            val c = v.getJSONObject(i)
            assertEquals("input #$i ${c.getString("in")}", c.getString("key"), TextNorm.key(c.getString("in")))
        }
    }

    @Test
    fun gradingMatchesPython() {
        val v = vectors.getJSONArray("grade")
        for (i in 0 until v.length()) {
            val c = v.getJSONObject(i)
            assertEquals("case #$i ${c.getString("answer")}", c.getString("signal"),
                gradeAnswer(c.optJSONObject("accept_answers"), c.getString("answer")))
        }
    }
}

object Repo {
    /** Unit tests run in android/app; the repository root is two levels up. */
    val root: File = generateSequence(File("").absoluteFile) { it.parentFile }
        .first { File(it, "contract/rest_contract.json").isFile }
}
