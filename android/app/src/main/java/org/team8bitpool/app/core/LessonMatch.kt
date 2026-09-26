package org.team8bitpool.app.core

/**
 * Port of lesson_match.py: match a recognised utterance to the content pack's
 * pre-translated lines (cosine similarity of character trigram counts of the
 * normalised text, numbers written as words; a match also needs the line's exact
 * numbers). Tested against
 * tests/data/lesson_match_vectors.json (LessonMatchTest). Thresholds:
 * config.LESSON_MATCH_THRESHOLD, tuned in bench/results/lesson_match.md.
 */
object LessonMatch {
    val HINDI_0_99: List<String> = ("शून्य एक दो तीन चार पांच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस " +
        "बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस " +
        "पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस " +
        "अड़तालीस उनचास पचास इक्यावन बावन तिरेपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ " +
        "तिरेसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर " +
        "छिहत्तर सतहत्तर अठहत्तर उन्यासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी " +
        "नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे").split(" ")

    /** Digit by digit, for numbers too long for the word forms (as Python does). */
    private fun digitWise(digits: String, lang: String) =
        digits.map { if (lang == "hi") HINDI_0_99[it - '0'] else OlChiki.NUMBER_WORDS.getValue(it - '0') }.joinToString(" ")

    fun hindiNumber(digits: String): String {
        val s = digits.trimStart('0').ifEmpty { "0" }
        if (s.length > 4) return digitWise(s, "hi")
        val n = s.toInt()
        if (n < 100) return HINDI_0_99[n]
        val th = n / 1000; val hu = (n % 1000) / 100; val r = n % 100
        val parts = ArrayList<String>()
        if (th != 0) { parts += HINDI_0_99[th]; parts += "हजार" }
        if (hu != 0) { parts += HINDI_0_99[hu]; parts += "सौ" }
        if (r != 0) parts += HINDI_0_99[r]
        return parts.joinToString(" ")
    }

    private fun numberWords(digits: String, lang: String): String {
        if (lang == "hi") return hindiNumber(digits)
        val s = digits.trimStart('0').ifEmpty { "0" }
        return if (s.length > 3) digitWise(s, "sat") else OlChiki.numberToSantali(s.toLong())
    }

    fun canonical(text: String, lang: String): String {
        val k = TextNorm.key(text)
        return TextNorm.key(Regex("[0-9]+").replace(k) { " ${numberWords(it.value, lang)} " })
    }

    private val HI_NUMBER_WORDS: Set<String> by lazy { (HINDI_0_99 + listOf("सौ", "हजार")).map { TextNorm.key(it) }.toSet() }
    private val SAT_NUMBER_WORDS: Set<String> by lazy { OlChiki.NUMBER_WORDS.values.map { TextNorm.key(it) }.toSet() }

    /** The number words of canonical(text), in order (port of lesson_match.number_tokens). */
    fun numberTokens(text: String, lang: String): List<String> {
        val words = if (lang == "hi") HI_NUMBER_WORDS else SAT_NUMBER_WORDS
        return canonical(text, lang).split(" ").filter { it in words }
    }

    fun trigrams(text: String, lang: String): Map<String, Int> {
        val s = " ${canonical(text, lang)} "
        val m = HashMap<String, Int>()
        // code points, as Python slices strings (every script used here is in the BMP)
        for (i in 0..s.length - 3) m.merge(s.substring(i, i + 3), 1, Int::plus)
        return m
    }

    private fun norm(t: Map<String, Int>) = Math.sqrt(t.values.sumOf { it.toDouble() * it })

    fun similarity(a: String, b: String, lang: String): Double {
        val ta = trigrams(a, lang); val tb = trigrams(b, lang)
        if (ta.isEmpty() || tb.isEmpty()) return 0.0
        val dot = ta.entries.sumOf { (k, v) -> v.toDouble() * (tb[k] ?: 0) }
        return dot / Math.sqrt(norm(ta) * norm(ta) * norm(tb) * norm(tb))
    }

    data class Result(val line: String?, val score: Double, val matched: Boolean, val numbersAgree: Boolean = false)

    /** The closest candidate (ties: the first in order), matched only when score >= threshold and the numbers agree. */
    fun match(text: String, candidates: Iterable<String>, threshold: Double, lang: String): Result {
        val t = trigrams(text, lang)
        if (t.isEmpty()) return Result(null, 0.0, false)
        val nt = norm(t)
        var top: String? = null; var score = 0.0
        for (c in candidates) {
            val tc = trigrams(c, lang)
            if (tc.isEmpty()) continue
            val s = t.entries.sumOf { (k, v) -> v.toDouble() * (tc[k] ?: 0) } / (nt * norm(tc))
            if (s > score) { top = c; score = s }
        }
        val agree = top != null && numberTokens(text, lang) == numberTokens(top, lang)
        return Result(top, score, top != null && score >= threshold && agree, agree)
    }
}
