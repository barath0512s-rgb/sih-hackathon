package org.team8bitpool.app.core

/**
 * Port of IndicTransToolkit's IndicProcessor (processor.pyx @ 3efb841) for the
 * tablet's translation (A5), with the IndicNLP parts it calls for Hindi and Santali:
 * the Devanagari and Oriya normalizers (Santali maps to "or" in the toolkit), the
 * trivial tokenizer / detokenizer and the Unicode transliterator. Read from the
 * installed sources, not guessed; upstream quirks are kept on purpose, because the
 * model was trained and is run with them:
 *   - the "colon after a letter becomes a visarga" rule has a malformed character
 *     class upstream ([\\u0900-\\u097f]): it fires after 0-9, :;<=>?@, A-Z, [, \, u, f
 *     (and b for Oriya) and writes a literal backslash, "1" and the visarga;
 *   - the detokenizer only joins a number sequence when text precedes it.
 * Placeholders (URLs, e-mails, long numbers) are numbered in order of first
 * occurrence (upstream: a Python set, whose order is not fixed). Tested against the
 * Python path: tests in NmtTest (android/app/src/test/resources/nmt_vectors.json).
 */
object IndicProc {
    // Python `regex` \s, \d, \w are Unicode; spelled out so desktop JVM and Android ICU agree.
    private const val S = "[\\t\\n\\u000B\\f\\r \\u001C-\\u001F\\u0085\\u00A0\\u1680\\u2000-\\u200A\\u2028\\u2029\\u202F\\u205F\\u3000]"
    private const val D = "\\p{Nd}"
    private const val W = "[\\p{L}\\p{Mn}\\p{Mc}\\p{Me}\\p{Nd}\\p{Pc}\\u200C\\u200D]"

    private val ISO = mapOf("hin_Deva" to "hi", "sat_Olck" to "or", "eng_Latn" to "en", "ory_Orya" to "or")

    private val DIGITS: Map<Char, Char> = buildMap {
        val zeros = listOf(0x09e6, 0x0ae6, 0x0ce6, 0x0966, 0x0660, 0xabf0, 0x0b66, 0x0a66, 0x1c50, 0x06f0)
        for (z in zeros) for (d in 0..9) put((z + d).toChar(), ('0' + d))
        // upstream lists Telugu from 1 to 9 only (no \u0c66)
        for (d in 1..9) put((0x0c66 + d).toChar(), ('0' + d))
    }

    private data class Rep(val re: Regex, val repl: (MatchResult) -> String)
    private val PUNC = listOf(
        Rep(Regex("\\r")) { "" },
        Rep(Regex("\\($S*")) { "(" },
        Rep(Regex("$S*\\)")) { ")" },
        Rep(Regex("$S:$S?")) { ":" },
        Rep(Regex("$S;$S?")) { ";" },
        Rep(Regex("[`´‘‚’]")) { "'" },
        Rep(Regex("[„“”«»]")) { "\"" },
        Rep(Regex("[–—]")) { "-" },
        Rep(Regex(" %")) { "%" },
        Rep(Regex(" [?!;]")) { it.value.trim() },
    )
    private val MULTISPACE = Regex("[ ]{2,}")
    private val END_BRACKET = Regex("\\) ([.!:?;,])")
    private val DIGIT_SPACE_PERCENT = Regex("($D) %")
    private val DOUBLE_QUOT_PUNC = Regex("\"([,.]+)")
    private val DIGIT_NBSP_DIGIT = Regex("($D) ($D)")

    // Python regex's \b treats a letter and its vowel sign as one word; Java's \b does not: spelled out.
    private const val B = "(?:(?<=$W)(?!$W)|(?<!$W)(?=$W))"
    private val URL = Regex("$B(?<![\\p{L}\\p{Mn}\\p{Mc}\\p{Nd}\\p{Pc}/.])(?:(?:https?|ftp)://)?(?:(?:[\\p{L}\\p{Mn}\\p{Mc}\\p{Nd}\\p{Pc}-]+\\.)+(?!\\.))(?:[\\p{L}\\p{Mn}\\p{Mc}\\p{Nd}\\p{Pc}/\\-?#&=%.]+)+(?!\\.$W)$B")
    private val NUMERAL = Regex("(~?$D+\\.?$D*$S?%?$S?-?$S?~?$D+\\.?$D*$S?%|~?$D+%|$D+[-/.,:']$D+[-/.,:'+]$D+(?:\\.$D+)?|$D+[-/.:'+]$D+(?:\\.$D+)?)")
    private val EMAIL = Regex("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}")
    private val OTHER = Regex("[A-Za-z0-9]*[#|@]$W+")

    private val INDIC_FAILURE_CASES = listOf(
        "آی ڈی ", "ꯑꯥꯏꯗꯤ", "आईडी", "आई . डी . ", "आई . डी .", "आई. डी. ", "आई. डी.", "आय. डी. ", "आय. डी.",
        "आय . डी . ",
        // upstream is missing a comma here, so these two are one string
        "आय . डी ." + "आइ . डी . ",
        "आइ . डी .", "आइ. डी. ", "आइ. डी.", "ऐटि", "آئی ڈی ", "ᱟᱭᱰᱤ ᱾", "आयडी", "ऐडि", "आइडि", "ᱟᱭᱰᱤ",
    )

    class Pre(val text: String, val placeholders: Map<String, String>)

    private fun puncNorm(t0: String): String {
        var t = t0
        for (r in PUNC) t = r.re.replace(t, r.repl)
        t = MULTISPACE.replace(t, " ")
        t = END_BRACKET.replace(t) { ")" + it.groupValues[1] }
        t = DIGIT_SPACE_PERCENT.replace(t) { it.groupValues[1] + "%" }
        t = DOUBLE_QUOT_PUNC.replace(t) { it.groupValues[1] + "\"" }
        t = DIGIT_NBSP_DIGIT.replace(t) { it.groupValues[1] + "." + it.groupValues[2] }
        return pyStrip(t)
    }

    /** Python str.strip(): Unicode whitespace at both ends. */
    private fun pyStrip(s: String) = s.trim { it.isWhitespace() || it == '\u001C' || it == '\u001D' || it == '\u001E' || it == '\u001F' || it == '\u0085' || it == '\u00A0' }

    private fun wrapPlaceholders(t0: String, map: LinkedHashMap<String, String>): String {
        var t = t0
        var serial = 1
        for (p in listOf(EMAIL, URL, NUMERAL, OTHER)) {
            val matches = LinkedHashSet<String>()
            for (m in p.findAll(t)) matches += if (p === NUMERAL) m.groupValues[1] else m.value
            for (m in matches) {
                if (p === URL && m.replace(".", "").length < 4) continue
                if (p === NUMERAL && m.replace(" ", "").replace(".", "").replace(":", "").length < 4) continue
                val n = serial
                for (k in listOf("<ID$n>", "< ID$n >", "[ID$n]", "[ ID$n ]", "[ID $n]", "<ID$n]", "< ID$n]", "<ID$n ]",
                                 "<id$n>", "< id$n >", "[id$n]", "[ id$n ]", "[id $n]", "<id$n]", "< id$n]", "<id$n ]")) map[k] = m
                for (c in INDIC_FAILURE_CASES) for (k in listOf("<$c$n>", "< $c$n >", "< $c $n >", "<$c $n]", "< $c $n ]",
                        "[$c$n]", "[$c $n]", "[ $c$n ]", "[ $c $n ]", "$c $n", "$c$n")) map[k] = m
                t = t.replace(m, "<ID$n>")
                serial++
            }
        }
        return Regex("$S+").replace(t, " ").replace(">/", ">").replace("]/", "]")
    }

    // ── IndicNLP normalizers (BaseNormalizer + Devanagari / Oriya) ─────────────
    private fun baseNormalize(t0: String): String {
        var t = t0.replace("\ufeff", "").replace("\ufffe", "").replace("\u2060", "").replace("\u00ad", "")
            .replace("\u200b", " ").replace("\u00a0", " ").replace("\u200c", "").replace("\u200d", "")
        t = t.replace("\ufeff", "").replace("„", "\"").replace("“", "\"").replace("”", "\"").replace("–", "-")
            .replace("—", " - ").replace("´", "'").replace("‘", "'").replace("‚", "'").replace("’", "'")
            .replace("''", "\"").replace("´´", "\"").replace("…", "...")
        return t
    }

    private val VISARGA_DEVA = Regex("[\\u0030-\\u005cuf]:")
    private val VISARGA_ORIYA = Regex("[\\u0030-\\u005cubf]:")

    private fun devanagari(t0: String): String {
        var t = baseNormalize(t0)
        val nukta = "\u093c"
        t = t.replace("\u0972", "\u090f").replace("\u0929", "\u0928$nukta").replace("\u0931", "\u0930$nukta")
            .replace("\u0934", "\u0933$nukta").replace("\u0958", "\u0915$nukta").replace("\u0959", "\u0916$nukta")
            .replace("\u095a", "\u0917$nukta").replace("\u095b", "\u091c$nukta").replace("\u095c", "\u0921$nukta")
            .replace("\u095d", "\u0922$nukta").replace("\u095e", "\u092b$nukta").replace("\u095f", "\u092f$nukta")
            .replace("|", "\u0964")
        return VISARGA_DEVA.replace(t) { "\\1\u0903" }
    }

    private fun oriya(t0: String): String {
        var t = baseNormalize(t0)
        t = t.replace("\u0b05\u0b3e", "\u0b06").replace("\u0b0f\u0b57", "\u0b10").replace("\u0b13\u0b57", "\u0b14")
            .replace("\u0b5c", "\u0b21\u0b3c").replace("\u0b5d", "\u0b22\u0b3c")
            .replace("\u0b64", "\u0964").replace("\u0b65", "\u0965").replace("\u0b7c", "\u0964")
            .replace("\u0b35", "\u0b2c").replace("\u0b47\u0b56", "\u0b58").replace("\u0b47\u0b3e", "\u0b4b")
            .replace("\u0b47\u0b57", "\u0b4c")
        return VISARGA_ORIYA.replace(t) { "\\1\u0b03" }
    }

    private fun normalizer(iso: String): (String) -> String = when (iso) {
        "hi" -> ::devanagari
        "or" -> ::oriya
        else -> error("no normalizer ported for $iso")
    }

    // ── IndicNLP trivial tokenizer / detokenizer ───────────────────────────────
    private const val PUNCT = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
    private val TOK = Regex("([" + PUNCT.map { "\\" + it }.joinToString("") + "\\u0964\\u0965\\uAAF1\\uAAF0\\uABEB\\uABEC\\uABED\\uABEE\\uABEF\\u1C7E\\u1C7F])")
    private val NUM_SEQ = Regex("([0-9]+ [,.:/] )+[0-9]+")

    fun trivialTokenize(text: String): List<String> {
        val tok = TOK.replace(text.replace("\t", " ")) { " " + it.value + " " }
        val s = Regex("[ ]+").replace(tok, " ").trim(' ')
        val sb = StringBuilder(); var prev = 0
        for (m in NUM_SEQ.findAll(s)) {
            if (m.range.first > prev) sb.append(s, prev, m.range.first)
            sb.append(m.value.replace(" ", "")); prev = m.range.last + 1
        }
        sb.append(s.substring(prev))
        return sb.toString().split(" ")
    }

    private val LA = Regex("[ ]([!%)\\]},.:;>?\\u0964\\u0965])")
    private val RA = Regex("([#$(\\[{<@])[ ]")
    private val LRA = Regex("[ ]([-/\\\\])[ ]")

    fun trivialDetokenize(text: String): String {
        var s = text
        val sb = StringBuilder(); var prev = 0
        for (m in NUM_SEQ.findAll(s)) {
            if (m.range.first > prev) {                  // upstream joins a number sequence only after other text
                sb.append(s, prev, m.range.first)
                sb.append(m.value.replace(" ", "")); prev = m.range.last + 1
            }
        }
        sb.append(s.substring(prev)); s = sb.toString()
        s = LRA.replace(s) { it.groupValues[1] }
        s = LA.replace(s) { it.groupValues[1] }
        s = RA.replace(s) { it.groupValues[1] }
        for (punc in listOf('\'', '"', '`')) {
            var cnt = 0
            val out = StringBuilder()
            for (c in s) {
                if (c == punc) { out.append(if (cnt % 2 == 0) "@RA" else "@LA"); cnt++ } else out.append(c)
            }
            s = out.toString().replace("@RA ", punc.toString()).replace(" @LA", punc.toString())
                .replace("@RA", punc.toString()).replace("@LA", punc.toString())
        }
        return s
    }

    private val RANGE = mapOf("hi" to 0x0900, "or" to 0x0B00)

    /** IndicNLP UnicodeIndicTransliterator.transliterate for the ported scripts. */
    fun transliterate(text: String, from: String, to: String): String {
        val a = RANGE[from] ?: return text; val b = RANGE[to] ?: return text
        val sb = StringBuilder(text.length)
        for (c in text) {
            val off = c.code - a
            sb.append(if (off in 0..0x6F && c != '\u0964' && c != '\u0965') (b + off).toChar() else c)
        }
        return sb.toString()
    }

    // ── IndicProcessor.preprocess / postprocess (inference) ────────────────────
    fun preprocess(sent0: String, srcLang: String, tgtLang: String): Pre {
        val iso = ISO[srcLang] ?: "hi"
        val script = srcLang.substringAfter("_")
        var sent = puncNorm(sent0)
        sent = sent.map { DIGITS[it] ?: it }.joinToString("")
        val map = LinkedHashMap<String, String>()
        sent = wrapPlaceholders(sent, map)
        val translit = script !in setOf("Arab", "Aran", "Olck", "Mtei", "Latn")
        require(iso != "en") { "English is not ported" }
        val normed = normalizer(iso)(pyStrip(sent))
        var joined = trivialTokenize(normed).joinToString(" ")
        if (translit) joined = transliterate(joined, iso, "hi").replace(" ् ", "्")
        return Pre("$srcLang $tgtLang ${pyStrip(joined)}", map)
    }

    fun postprocess(sent0: String, lang: String, placeholders: Map<String, String>): String {
        var sent = sent0
        for ((k, v) in placeholders) sent = sent.replace(k, v)
        val iso = ISO[lang] ?: "hi"
        return trivialDetokenize(transliterate(sent, "hi", iso))
    }
}
