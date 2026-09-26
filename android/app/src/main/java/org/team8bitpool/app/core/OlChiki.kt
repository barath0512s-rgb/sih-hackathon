package org.team8bitpool.app.core

import java.text.Normalizer

/**
 * Port of translit/olchiki.py: Ol Chiki (Santali) -> Devanagari / Latin, so the
 * Hindi Piper voice can read Santali on the tablet (M2). Same structure as the
 * Python module (parse -> tokens -> render) and the same rules; the rules and why
 * are documented there. The test-only Aksharamukha "compat" mode is not ported.
 * Tested against tests/data/olchiki_vectors.json (OlChikiTest).
 */
object OlChiki {
    private val VOWEL_LETTERS = mapOf('ᱚ' to 'o', 'ᱟ' to 'a', 'ᱤ' to 'i', 'ᱩ' to 'u', 'ᱮ' to 'e', 'ᱳ' to 'O')
    private const val CONSONANTS = "ᱛᱜᱝᱞᱠᱡᱢᱣᱥᱦᱧᱨᱪᱫᱬᱭᱯᱰᱱᱲᱴᱵᱶ"
    private const val OH = 'ᱷ'
    private const val CHECKED = "ᱜᱡᱫᱵ"
    private const val AHAD = 'ᱽ'
    private const val GAAHLAA = 'ᱹ'
    private const val MU_GAAHLAA = 'ᱺ'
    private const val MU_TTUDDAG = 'ᱸ'
    private const val RELAA = 'ᱻ'
    private const val PHAARKAA = 'ᱼ'

    private fun digitValue(c: Char): Int? = when (c) {
        in '᱐'..'᱙' -> c - '᱐'
        in '०'..'९' -> c - '०'
        in '0'..'9' -> c - '0'
        else -> null
    }

    private val CONS_DEVA = mapOf(
        'ᱛ' to "त", 'ᱜ' to "ग", 'ᱝ' to "ङ", 'ᱞ' to "ल", 'ᱠ' to "क", 'ᱡ' to "ज", 'ᱢ' to "म",
        'ᱣ' to "व", 'ᱥ' to "स", 'ᱦ' to "ह", 'ᱧ' to "ञ", 'ᱨ' to "र", 'ᱪ' to "च", 'ᱫ' to "द",
        'ᱬ' to "ण", 'ᱭ' to "य", 'ᱯ' to "प", 'ᱰ' to "ड", 'ᱱ' to "न", 'ᱲ' to "ड़", 'ᱴ' to "ट",
        'ᱵ' to "ब", 'ᱶ' to "व",
    )
    private val CHECKED_DEVA = mapOf('ᱜ' to "क", 'ᱡ' to "च", 'ᱫ' to "त", 'ᱵ' to "प")
    private val ASPIRATE_DEVA = mapOf("क" to "ख", "ग" to "घ", "च" to "छ", "ज" to "झ", "त" to "थ", "द" to "ध",
        "प" to "फ", "ब" to "भ", "ट" to "ठ", "ड" to "ढ", "ड़" to "ढ़")
    private val VOWEL_DEVA = mapOf('o' to ("ऑ" to "ॉ"), 'a' to ("आ" to "ा"), 'i' to ("इ" to "ि"), 'u' to ("उ" to "ु"),
        'e' to ("ए" to "े"), 'O' to ("ओ" to "ो"), '@' to ("अ" to ""))
    private val LONG_DEVA = mapOf('i' to ("ई" to "ी"), 'u' to ("ऊ" to "ू"))
    private const val VIRAMA = "्"
    private const val CANDRABINDU = "ँ"
    private const val ANUSVARA = "ं"

    private val CONS_LAT = mapOf(
        'ᱛ' to "t", 'ᱜ' to "g", 'ᱝ' to "ng", 'ᱞ' to "l", 'ᱠ' to "k", 'ᱡ' to "j", 'ᱢ' to "m",
        'ᱣ' to "w", 'ᱥ' to "s", 'ᱦ' to "h", 'ᱧ' to "ny", 'ᱨ' to "r", 'ᱪ' to "ch", 'ᱫ' to "d",
        'ᱬ' to "n", 'ᱭ' to "y", 'ᱯ' to "p", 'ᱰ' to "d", 'ᱱ' to "n", 'ᱲ' to "r", 'ᱴ' to "t",
        'ᱵ' to "b", 'ᱶ' to "w",
    )
    private val CHECKED_LAT = mapOf('ᱜ' to "k", 'ᱡ' to "ch", 'ᱫ' to "t", 'ᱵ' to "p")
    private val VOWEL_LAT = mapOf('o' to "o", 'a' to "a", 'i' to "i", 'u' to "u", 'e' to "e", 'O' to "o", '@' to "a")
    private val LONG_LAT = mapOf('i' to "ee", 'u' to "oo")
    private val PUNCT = mapOf("᱾" to ("।" to "."), "᱿" to ("॥" to "."), "।" to ("।" to "."), "॥" to ("॥" to "."))

    /** Santali number words (education_glossary.NUMBERS_HI_SAT via olchiki._number_words). */
    val NUMBER_WORDS = mapOf(0 to "ᱥᱩᱱᱩᱢ", 1 to "ᱢᱤᱫ", 2 to "ᱵᱟᱨ", 3 to "ᱯᱮ", 4 to "ᱯᱩᱱ", 5 to "ᱢᱚᱬᱮ",
        6 to "ᱛᱩᱨᱩᱭ", 7 to "ᱮᱭᱟᱭ", 8 to "ᱤᱨᱟᱹᱞ", 9 to "ᱟᱨᱮ", 10 to "ᱜᱮᱞ", 100 to "ᱥᱟᱭ")

    fun numberToSantali(n: Long): String {
        val w = NUMBER_WORDS
        require(n >= 0) { "negative numbers are not supported" }
        if (n < 10) return w.getValue(n.toInt())
        if (n < 100) {
            val t = (n / 10).toInt(); val u = (n % 10).toInt()
            return (listOfNotNull(if (t > 1) w[t] else null, w[10], if (u != 0) w[u] else null)).joinToString(" ")
        }
        if (n < 1000) {
            val h = (n / 100).toInt(); val r = n % 100
            return (listOfNotNull(if (h > 1) w[h] else null, w[100], if (r != 0L) numberToSantali(r) else null)).joinToString(" ")
        }
        return n.toString().map { w.getValue(it - '0') }.joinToString(" ")
    }

    private class Vowel(var q: Char, var nasal: Boolean = false, var long: Boolean = false)
    private class Cons(val c: Char, var asp: Boolean = false, var voiced: Boolean = false, var v: Vowel? = null, val oh: Boolean = false)
    private sealed class Tok {
        class C(val x: Cons) : Tok()
        class V(val v: Vowel) : Tok()
        class N(val digits: String) : Tok()
        class P(val s: String) : Tok()
        object B : Tok()
    }

    private fun parse(input: String): List<Tok> {
        val text = Normalizer.normalize(input, Normalizer.Form.NFC)
        val toks = ArrayList<Tok>()
        val n = text.length
        var i = 0
        fun vowelAt(start: Int): Pair<Vowel, Int> {
            var j = start
            val v = Vowel(VOWEL_LETTERS.getValue(text[j]))
            j++
            while (j < n && text[j] in charArrayOf(GAAHLAA, MU_GAAHLAA, MU_TTUDDAG, RELAA)) {
                val m = text[j]
                if ((m == GAAHLAA || m == MU_GAAHLAA) && v.q == 'a') v.q = '@'
                if (m == MU_GAAHLAA || m == MU_TTUDDAG) v.nasal = true
                if (m == RELAA) v.long = true
                j++
            }
            return v to j
        }
        while (i < n) {
            val ch = text[i]
            when {
                digitValue(ch) != null -> {
                    var j = i
                    while (j < n && digitValue(text[j]) != null) j++
                    toks.add(Tok.N(text.substring(i, j))); i = j
                }
                ch in CONSONANTS -> {
                    val c = Cons(ch)
                    i++
                    while (i < n && (text[i] == OH || text[i] == AHAD)) {
                        if (text[i] == OH) c.asp = true else c.voiced = true
                        i++
                    }
                    if (i < n && text[i] in VOWEL_LETTERS) {
                        val (v, j) = vowelAt(i); c.v = v; i = j
                    } else if (i < n && (text[i] == MU_TTUDDAG || text[i] == MU_GAAHLAA || text[i] == GAAHLAA)) {
                        c.v = Vowel('@', nasal = text[i] != GAAHLAA); i++
                    }
                    toks.add(Tok.C(c))
                }
                ch in VOWEL_LETTERS -> { val (v, j) = vowelAt(i); toks.add(Tok.V(v)); i = j }
                ch == OH -> {
                    val c = Cons('ᱦ', oh = true)
                    i++
                    if (i < n && text[i] in VOWEL_LETTERS) { val (v, j) = vowelAt(i); c.v = v; i = j }
                    toks.add(Tok.C(c))
                }
                ch == PHAARKAA -> { toks.add(Tok.B); i++ }
                ch == AHAD || ch == GAAHLAA || ch == MU_GAAHLAA || ch == MU_TTUDDAG || ch == RELAA -> i++
                else -> {
                    // a supplementary-plane character stays one token, as in Python
                    val cp = text.codePointAt(i); val len = Character.charCount(cp)
                    toks.add(Tok.P(text.substring(i, i + len))); i += len
                }
            }
        }
        return toks
    }

    private fun prevHasVowel(toks: List<Tok>, k: Int): Boolean {
        if (k == 0) return false
        val p = toks[k - 1]
        return p is Tok.V || (p is Tok.C && p.x.v != null)
    }

    private fun devaVowel(v: Vowel) = if (v.long && v.q in LONG_DEVA) LONG_DEVA.getValue(v.q) else VOWEL_DEVA.getValue(v.q)

    private fun renderDeva(toks: List<Tok>, digits: String): String {
        val out = StringBuilder()
        for ((k, t) in toks.withIndex()) {
            when (t) {
                is Tok.B -> {}
                is Tok.N -> out.append(renderNumber(t.digits, digits, deva = true))
                is Tok.P -> out.append(PUNCT[t.s]?.first ?: t.s)
                is Tok.V -> out.append(devaVowel(t.v).first).append(if (t.v.nasal) CANDRABINDU else "")
                is Tok.C -> {
                    val x = t.x; val v = x.v
                    if (v == null && x.c == 'ᱝ' && prevHasVowel(toks, k)) { out.append(ANUSVARA); continue }
                    val checked = v == null && x.c in CHECKED && !x.voiced
                    var base = if (checked) CHECKED_DEVA.getValue(x.c) else CONS_DEVA.getValue(x.c)
                    if (x.asp) base = ASPIRATE_DEVA[base] ?: (base + VIRAMA + "ह")
                    if (v == null) out.append(base).append(VIRAMA)
                    else out.append(base).append(devaVowel(v).second).append(if (v.nasal) CANDRABINDU else "")
                }
            }
        }
        return out.toString()
    }

    private fun latVowel(v: Vowel) =
        (if (v.long && v.q in LONG_LAT) LONG_LAT.getValue(v.q) else VOWEL_LAT.getValue(v.q)) + (if (v.nasal) "n" else "")

    private fun renderLatin(toks: List<Tok>, digits: String): String {
        val out = StringBuilder()
        for (t in toks) {
            when (t) {
                is Tok.B -> {}
                is Tok.N -> out.append(renderNumber(t.digits, digits, deva = false))
                is Tok.P -> out.append(PUNCT[t.s]?.second ?: t.s)
                is Tok.V -> out.append(latVowel(t.v))
                is Tok.C -> {
                    val x = t.x; val v = x.v
                    var base = if (v == null && x.c in CHECKED && !x.voiced) CHECKED_LAT.getValue(x.c) else CONS_LAT.getValue(x.c)
                    if (x.asp) base += "h"
                    out.append(base).append(if (v != null) latVowel(v) else "")
                }
            }
        }
        return out.toString()
    }

    private fun renderNumber(digitStr: String, digits: String, deva: Boolean): String {
        val ds = digitStr.map { digitValue(it)!! }
        if (digits == "digits") {
            return if (deva) ds.joinToString("") { (0x0966 + it).toChar().toString() }
            else ds.joinToString("").trimStart('0').ifEmpty { "0" }
        }
        val words = numberToSantali(ds.joinToString("").toBigInteger().toLong())
        val r = if (deva) renderDeva(parse(words), "spoken") else renderLatin(parse(words), "spoken")
        return " $r "
    }

    private fun tidy(s: String): String =
        s.replace(Regex("[ \\t]+"), " ").replace(Regex(" ([।॥.,?!])"), "$1").trim()

    fun toDevanagari(text: String, digits: String = "spoken"): String {
        require(digits == "spoken" || digits == "digits") { "digits must be 'spoken' or 'digits'" }
        return tidy(renderDeva(parse(text), digits))
    }

    fun toLatin(text: String, digits: String = "spoken"): String {
        require(digits == "spoken" || digits == "digits") { "digits must be 'spoken' or 'digits'" }
        return tidy(renderLatin(parse(text), digits))
    }

    fun hasOlChiki(text: String) = text.any { it.code in 0x1C50..0x1C7F }
}
