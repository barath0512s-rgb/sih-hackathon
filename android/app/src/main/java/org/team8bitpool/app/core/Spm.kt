package org.team8bitpool.app.core

import java.io.File
import java.io.InputStream
import java.text.Normalizer
import java.util.PriorityQueue

/**
 * SentencePiece BPE encoding in Kotlin (A5), for IndicTrans2's model.SRC / model.TGT
 * (model_type BPE, normalizer nmt_nfkc, add_dummy_prefix, remove_extra_whitespaces,
 * escape_whitespaces; no byte fallback). The merge loop follows sentencepiece's
 * bpe_model.cc: characters (user-defined symbols kept whole), then repeatedly the
 * adjacent pair whose concatenation is a piece with the highest score (ties: the
 * leftmost). Normalisation: Java NFKC plus the whitespace rules; the model's
 * precompiled nmt_nfkc table is not parsed (the golden test measures how often
 * that matters: NmtTest, >= 98 % identical ids is the bar).
 */
class Spm(private val pieces: Map<String, Float>, private val userDefined: List<String>) {

    fun normalize(text: String): String {
        val sb = StringBuilder()
        for (ch in Normalizer.normalize(text, Normalizer.Form.NFKC)) {
            when {
                ch == '\t' || ch == '\n' || ch == '\r' || Character.isSpaceChar(ch) -> sb.append(' ')
                ch.code < 0x20 || ch.code == 0x7F -> {}                    // control characters are dropped
                else -> sb.append(ch)
            }
        }
        // remove_extra_whitespaces, add_dummy_prefix, escape_whitespaces
        val s = sb.toString().trim(' ').replace(Regex(" +"), " ")
        return "▁" + s.replace(' ', '▁')
    }

    private class Sym(var piece: String, var prev: Int, var next: Int, val freeze: Boolean)
    private class Pair(val left: Int, val right: Int, val score: Float, val size: Int)

    fun encodeAsPieces(text: String): List<String> {
        val s = normalize(text)
        if (s == "▁") return emptyList()
        val syms = ArrayList<Sym>()
        var i = 0
        while (i < s.length) {
            val ud = userDefined.firstOrNull { s.startsWith(it, i) }
            val len = ud?.length ?: Character.charCount(s.codePointAt(i))
            syms += Sym(s.substring(i, i + len), syms.size - 1, syms.size + 1, ud != null)
            i += len
        }
        syms.last().next = -1
        val agenda = PriorityQueue<Pair>(compareBy<Pair>({ -it.score }, { it.left }))
        fun maybeAdd(l: Int, r: Int) {
            if (l < 0 || r < 0 || syms[l].freeze || syms[r].freeze) return
            val p = syms[l].piece + syms[r].piece
            val score = pieces[p] ?: return
            agenda.add(Pair(l, r, score, p.length))
        }
        for (k in 1 until syms.size) maybeAdd(k - 1, k)
        while (agenda.isNotEmpty()) {
            val top = agenda.poll()
            val l = syms[top.left]; val r = syms[top.right]
            if (l.piece.isEmpty() || r.piece.isEmpty() || l.piece.length + r.piece.length != top.size) continue
            l.piece += r.piece
            l.next = r.next
            if (r.next >= 0) syms[r.next].prev = top.left
            r.piece = ""
            maybeAdd(l.prev, top.left)
            maybeAdd(top.left, l.next)
        }
        return syms.filter { it.piece.isNotEmpty() }.map { it.piece }
    }

    companion object {
        /** Reads the pieces (normal: merge candidates with their scores; user-defined: kept whole) from a .model file. */
        fun load(f: File): Spm = f.inputStream().use { load(it) }

        fun load(input: InputStream): Spm {
            val b = input.readBytes()
            val pieces = HashMap<String, Float>(200_000)
            val ud = ArrayList<String>()
            var pos = 0
            fun varint(): Long { var r = 0L; var sh = 0; while (true) { val x = b[pos++].toInt() and 0xff; r = r or ((x and 0x7f).toLong() shl sh); if (x < 0x80) return r; sh += 7 } }
            while (pos < b.size) {
                val key = varint().toInt(); val field = key ushr 3; val wt = key and 7
                when (wt) {
                    0 -> varint()
                    1 -> pos += 8
                    5 -> pos += 4
                    2 -> {
                        val len = varint().toInt(); val end = pos + len
                        if (field == 1) {                              // SentencePiece { piece=1, score=2, type=3 }
                            var piece = ""; var score = 0f; var type = 1
                            while (pos < end) {
                                val k2 = varint().toInt(); val f2 = k2 ushr 3; val w2 = k2 and 7
                                when {
                                    f2 == 1 && w2 == 2 -> { val l = varint().toInt(); piece = String(b, pos, l, Charsets.UTF_8); pos += l }
                                    f2 == 2 && w2 == 5 -> { score = java.lang.Float.intBitsToFloat((b[pos].toInt() and 0xff) or ((b[pos + 1].toInt() and 0xff) shl 8) or ((b[pos + 2].toInt() and 0xff) shl 16) or ((b[pos + 3].toInt() and 0xff) shl 24)); pos += 4 }
                                    f2 == 3 && w2 == 0 -> type = varint().toInt()
                                    w2 == 0 -> varint()
                                    w2 == 2 -> { val l = varint().toInt(); pos += l }
                                    w2 == 5 -> pos += 4
                                    w2 == 1 -> pos += 8
                                }
                            }
                            when (type) { 1 -> pieces[piece] = score; 4 -> ud += piece }
                        }
                        pos = end
                    }
                    else -> error("unexpected wire type $wt")
                }
            }
            return Spm(pieces, ud.sortedByDescending { it.length })
        }
    }
}

/** IndicTrans2's tokenizer (tokenization_indictrans.py): language tags + SentencePiece pieces -> ids, and back. */
class NmtTokenizer(private val srcSpm: Spm, private val srcDict: Map<String, Int>, tgtDict: Map<String, Int>) {
    private val tgtVocab: Map<Int, String> = tgtDict.entries.associate { it.value to it.key }
    val eos = 2; val unk = 3
    private val special = setOf(0, 1, 2, 3)

    /** "hin_Deva sat_Olck <text>" -> input ids with eos, as tokenizer([pre]).input_ids. */
    fun encode(pre: String): IntArray {
        val parts = pre.split(" ", limit = 3)
        val toks = listOf(parts[0], parts[1]) + srcSpm.encodeAsPieces(parts.getOrElse(2) { "" })
        return (toks.map { srcDict[it] ?: srcDict["<unk>"] ?: unk } + eos).toIntArray()
    }

    fun pieces(pre: String): List<String> {
        val parts = pre.split(" ", limit = 3)
        return listOf(parts[0], parts[1]) + srcSpm.encodeAsPieces(parts.getOrElse(2) { "" }) + "</s>"
    }

    /** batch_decode(..., skip_special_tokens=True, clean_up_tokenization_spaces=True). */
    fun decode(ids: List<Int>): String {
        val s = ids.filter { it !in special }.joinToString("") { tgtVocab[it] ?: "<unk>" }.replace('▁', ' ').trim()
        return s.replace(" .", ".").replace(" ?", "?").replace(" !", "!").replace(" ,", ",").replace(" ' ", "'")
            .replace(" n't", "n't").replace(" 'm", "'m").replace(" 's", "'s").replace(" 've", "'ve").replace(" 're", "'re")
    }

    companion object {
        fun dict(f: File): Map<String, Int> {
            val o = org.json.JSONObject(f.readText())
            val m = HashMap<String, Int>(o.length() * 2)
            for (k in o.keys()) m[k] = o.getInt(k)
            return m
        }
    }
}
