package org.team8bitpool.app.core

/** Port of nmt_guard.py (the int8 engine's length cap and stem-loop guard); same constants. */
object NmtGuard {
    private const val STEM_LETTERS = 3
    private const val WINDOW = 4
    private const val DISTINCT = 3
    private const val PUNCT = ",.?!।॥᱾᱿;:"

    fun lengthCap(nInput: Int, factor: Double = 2.0, margin: Int = 10, hardMax: Int = 128) =
        minOf(hardMax, Math.ceil(factor * nInput).toInt() + margin)

    fun stemLoop(words: List<String>): Boolean {
        if (words.size < WINDOW) return false
        val w = words.takeLast(WINDOW).map { it.trim { c -> c in PUNCT } }
        if (w.any { it.codePointCount(0, it.length) < STEM_LETTERS }) return false
        val stems = w.map { it.substring(0, it.offsetByCodePoints(0, STEM_LETTERS)) }.toSet()
        return stems.size == 1 && w.toSet().size >= DISTINCT
    }

    fun firstLoop(words: List<String>): Int? {
        for (k in WINDOW..words.size) if (stemLoop(words.subList(0, k))) return k
        return null
    }

    /** (text, cut): the text up to and including the first word of the loop. */
    fun cutStemLoop(text: String): kotlin.Pair<String, Boolean> {
        val words = pySplit(text)
        val k = firstLoop(words) ?: return text to false
        return words.subList(0, k - WINDOW + 1).joinToString(" ") to true
    }

    /** Python str.split(): runs of whitespace, no empty strings. */
    fun pySplit(s: String): List<String> {
        val out = ArrayList<String>(); val cur = StringBuilder()
        for (c in s) {
            if (c.isWhitespace() || c in '\u001C'..'\u001F' || c == '\u0085') { if (cur.isNotEmpty()) { out += cur.toString(); cur.clear() } }
            else cur.append(c)
        }
        if (cur.isNotEmpty()) out += cur.toString()
        return out
    }
}
