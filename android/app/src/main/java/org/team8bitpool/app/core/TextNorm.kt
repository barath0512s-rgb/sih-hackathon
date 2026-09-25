package org.team8bitpool.app.core

import java.text.Normalizer

/**
 * Port of textnorm.normalize_key (Python). Must give the same key for every
 * input in tests/data/normalize_key_vectors.json (TextNormTest).
 *
 * NFC; nukta removed; chandrabindu -> anusvara; zero-width marks removed;
 * Devanagari and Ol Chiki digits -> ASCII; every punctuation mark -> space;
 * whitespace collapsed; lower case.
 */
object TextNorm {
    private const val NUKTA = '़'
    private const val CHANDRABINDU = 'ँ'
    private const val ANUSVARA = 'ं'
    private val INVISIBLE = setOf('​', '‌', '‍', '﻿')

    private fun isPunctuation(cp: Int): Boolean = when (Character.getType(cp)) {
        Character.CONNECTOR_PUNCTUATION.toInt(), Character.DASH_PUNCTUATION.toInt(),
        Character.START_PUNCTUATION.toInt(), Character.END_PUNCTUATION.toInt(),
        Character.INITIAL_QUOTE_PUNCTUATION.toInt(), Character.FINAL_QUOTE_PUNCTUATION.toInt(),
        Character.OTHER_PUNCTUATION.toInt() -> true
        else -> false
    }

    private fun digit(c: Char): Char? = when (c) {
        in '०'..'९' -> '0' + (c - '०')
        in '᱐'..'᱙' -> '0' + (c - '᱐')
        else -> null
    }

    fun key(text: String?): String {
        if (text.isNullOrEmpty()) return ""
        val s = Normalizer.normalize(text, Normalizer.Form.NFC)
        val sb = StringBuilder(s.length)
        var i = 0
        while (i < s.length) {
            val cp = s.codePointAt(i)
            val n = Character.charCount(cp)
            if (n == 1) {
                val c = s[i]
                when {
                    c == NUKTA || c in INVISIBLE -> {}
                    c == CHANDRABINDU -> sb.append(ANUSVARA)
                    digit(c) != null -> sb.append(digit(c))
                    isPunctuation(cp) -> sb.append(' ')
                    else -> sb.append(c)
                }
            } else {
                if (isPunctuation(cp)) sb.append(' ') else sb.appendCodePoint(cp)
            }
            i += n
        }
        return collapse(sb).lowercase(java.util.Locale.ROOT)
    }

    /** Python's re.sub(r"\s+", " ", s).strip() over Unicode whitespace, without a
     *  regex: Android's ICU regex rejects (?U), and desktop Java's "\s" is ASCII-only. */
    private fun collapse(s: CharSequence): String {
        val out = StringBuilder(s.length)
        var pendingSpace = false
        for (c in s) {
            if (Character.isWhitespace(c) || Character.isSpaceChar(c)) { pendingSpace = out.isNotEmpty(); continue }
            if (pendingSpace) { out.append(' '); pendingSpace = false }
            out.append(c)
        }
        return out.toString()
    }
}
