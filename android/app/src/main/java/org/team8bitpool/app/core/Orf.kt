package org.team8bitpool.app.core

import org.json.JSONArray
import org.json.JSONObject

/**
 * Port of orf.py (C1): align a child's recognised reading to the passage; words
 * correct per minute. Same statuses, near-spelling rule and NIPUN bands; tested
 * against the Python cases (OrfTest).
 */
object Orf {
    const val NEAR = 0.75

    private fun sim(a: String, b: String): Double {
        if (a == b) return 1.0
        val n = a.length; val m = b.length
        var prev = IntArray(m + 1) { it }
        for (i in 1..n) {
            val cur = IntArray(m + 1); cur[0] = i
            for (j in 1..m) cur[j] = minOf(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + if (a[i - 1] != b[j - 1]) 1 else 0)
            prev = cur
        }
        return 1.0 - prev[m].toDouble() / maxOf(n, m)
    }

    /** Python str.split() then drop words that normalise to nothing. */
    private fun rawWords(t: String) = NmtGuard.pySplit(t).filter { TextNorm.key(it).isNotEmpty() }

    fun score(passage: String, spoken: String, seconds: Double, near: Double? = NEAR): JSONObject {
        val raw = rawWords(passage); val P = raw.map { TextNorm.key(it) }
        val sRaw = rawWords(spoken); val S = sRaw.map { TextNorm.key(it) }
        val n = P.size; val m = S.size
        val ok = Array(n) { i -> BooleanArray(m) { j -> P[i] == S[j] || (near != null && sim(P[i], S[j]) >= near) } }
        val D = Array(n + 1) { IntArray(m + 1) }
        for (i in 1..n) D[i][0] = i
        for (j in 1..m) D[0][j] = j
        for (i in 1..n) for (j in 1..m)
            D[i][j] = minOf(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + if (ok[i - 1][j - 1]) 0 else 1)
        val status = Array(n) { "omitted" }; val heard = arrayOfNulls<String>(n); val extra = ArrayList<String>()
        var i = n; var j = m; var last = -1
        val ops = ArrayList<Triple<String, Int, Int>>()
        while (i > 0 || j > 0) {
            if (i > 0 && j > 0 && D[i][j] == D[i - 1][j - 1] + if (ok[i - 1][j - 1]) 0 else 1) {
                ops += Triple(if (ok[i - 1][j - 1]) "ok" else "sub", i - 1, j - 1); i--; j--
            } else if (i > 0 && D[i][j] == D[i - 1][j] + 1) { ops += Triple("del", i - 1, -1); i-- }
            else { ops += Triple("ins", -1, j - 1); j-- }
        }
        for ((op, pi, sj) in ops.asReversed()) {
            when (op) {
                "ok", "sub" -> { status[pi] = if (op == "ok") "correct" else "error"; heard[pi] = sRaw[sj]; last = maxOf(last, pi) }
                "ins" -> extra += sRaw[sj]
            }
        }
        for (k in last + 1 until n) status[k] = "not_reached"
        val correct = status.count { it == "correct" }
        val errors = status.count { it == "error" || it == "omitted" }
        val attempted = correct + errors
        val minutes = seconds / 60
        val words = JSONArray()
        for (k in 0 until n) words.put(JSONObject().put("word", raw[k]).put("status", status[k]).put("heard", heard[k] ?: JSONObject.NULL))
        return JSONObject().put("words", words).put("extra", JSONArray(extra)).put("correct", correct).put("errors", errors)
            .put("omitted", status.count { it == "omitted" }).put("attempted", attempted)
            .put("seconds", Math.round(seconds * 100) / 100.0)
            .put("wcpm", if (minutes > 0) Math.round(correct / minutes * 10) / 10.0 else JSONObject.NULL)
            .put("accuracy", if (attempted > 0) Math.round(correct * 1000.0 / attempted) / 1000.0 else JSONObject.NULL)
    }

    fun nipunBand(grade: String, wcpm: Double?): JSONObject? = when {
        wcpm == null -> null
        grade == "2" -> JSONObject().put("lakshya", "NIPUN-G2-LIT-2").put("goal", "45-60 words per minute").put("met", wcpm >= 45)
        grade == "3" -> JSONObject().put("lakshya", "NIPUN-G3-LIT-2").put("goal", "at least 60 words per minute").put("met", wcpm >= 60)
        else -> null
    }
}
