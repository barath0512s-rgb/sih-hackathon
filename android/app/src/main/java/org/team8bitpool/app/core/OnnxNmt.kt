package org.team8bitpool.app.core

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.io.File
import java.nio.LongBuffer

/**
 * IndicTrans2 int8 on the tablet (A5 / M4): port of nmt_onnx.OnnxNMT with the int8
 * guard, over the three graphs of tools/export/export_indictrans2_onnx.py
 * (encoder, decoder_init, decoder_step with the key/value cache). Greedy, no-repeat
 * 3-gram, the int8 length cap and the stem-loop stop and cut (NmtGuard), and the
 * ported IndicProcessor (IndicProc) and tokenizer (Spm, NmtTokenizer).
 * Loaded on demand and closed after use when memory is short (SherpaSpeech unloads
 * the recogniser first).
 */
class OnnxNmt(dir: File, tokDir: File = dir, threads: Int = 2) : AutoCloseable {
    private val env = OrtEnvironment.getEnvironment()
    private val opts = OrtSession.SessionOptions().apply {
        setIntraOpNumThreads(threads); setInterOpNumThreads(1)
        setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
        // Defaults, as on the laptop. Tried on the 2 GB emulator: no arena / no memory patterns did not
        // lower the peak (1010 MB); no pre-packing saved 30 MB but doubled the time per sentence.
    }
    private val enc = env.createSession(File(dir, "encoder.int8.onnx").path, opts)
    private val init = env.createSession(File(dir, "decoder_init.int8.onnx").path, opts)
    private val step = env.createSession(File(dir, "decoder_step.int8.onnx").path, opts)
    private val nLayers = step.outputNames.count { it.endsWith(".self_k") }
    private val stepInputs = step.inputNames.toSet()
    val tokenizer = NmtTokenizer(Spm.load(File(tokDir, "model.SRC")), NmtTokenizer.dict(File(tokDir, "dict.SRC.json")),
                                 NmtTokenizer.dict(File(tokDir, "dict.TGT.json")))
    private val start = 2; private val eos = 2
    var lastCut = false; private set
    var lastSeq: List<Int> = emptyList(); private set

    private fun ids(a: IntArray) = OnnxTensor.createTensor(env, LongBuffer.wrap(a.map { it.toLong() }.toLongArray()), longArrayOf(1, a.size.toLong()))

    private fun banned(tokens: List<Int>, n: Int): Set<Int> {
        if (tokens.size < n) return emptySet()
        val prefix = tokens.subList(tokens.size - (n - 1), tokens.size)
        val out = HashSet<Int>()
        for (i in 0..tokens.size - n) if (tokens.subList(i, i + n - 1) == prefix) out += tokens[i + n - 1]
        return out
    }

    @Synchronized
    fun generate(input: IntArray, maxNew: Int, stop: ((List<Int>) -> Boolean)?): List<Int> {
        val inIds = ids(input); val mask = ids(IntArray(input.size) { 1 })
        val hid = enc.run(mapOf("input_ids" to inIds, "attention_mask" to mask))
        val hidT = hid.get(0) as OnnxTensor
        val startT = ids(intArrayOf(start))
        var res = init.run(mapOf("decoder_input_ids" to startT, "encoder_hidden_states" to hidT, "encoder_attention_mask" to mask))
        val names = init.outputNames.toList()
        val cross = HashMap<String, OnnxTensor>()
        val self = HashMap<String, OnnxTensor>()
        for ((k, name) in names.withIndex()) {
            if (k == 0) continue
            val t = res.get(k) as OnnxTensor
            val i = name.substringAfter("present.").substringBefore("."); val kind = name.substringAfterLast(".")
            if (kind.startsWith("cross")) cross["past.$i.$kind"] = t else self["past.$i.$kind"] = t
        }
        var logits = (res.get(0) as OnnxTensor)
        val seq = arrayListOf(start)
        val results = arrayListOf(res)
        try {
            for (s in 0 until maxNew) {
                // Read through the Java heap: getFloatBuffer() copies into a direct buffer that is
                // freed only on a GC, which grew native memory by ~0.5 MB a step (1010 -> 1499 MB).
                @Suppress("UNCHECKED_CAST")
                val row = (logits.value as Array<Array<FloatArray>>)[0].last()
                val ban = banned(seq, 3)
                var best = -1; var bestV = Float.NEGATIVE_INFINITY
                for (v in row.indices) {
                    if (v in ban) continue
                    val x = row[v]
                    if (x > bestV) { bestV = x; best = v }
                }
                seq += best
                if (best == eos) break
                if (stop != null && seq.size % 4 == 0 && stop(seq)) break
                val feed = HashMap<String, OnnxTensor>()
                feed["decoder_input_ids"] = ids(intArrayOf(best))
                feed["encoder_hidden_states"] = hidT; feed["encoder_attention_mask"] = mask
                feed.putAll(self); feed.putAll(cross)
                val r = step.run(feed.filterKeys { it in stepInputs })
                feed["decoder_input_ids"]!!.close()
                results += r
                logits = r.get(0) as OnnxTensor
                val sn = step.outputNames.toList()
                self.clear()
                for ((k, name) in sn.withIndex()) {
                    if (k == 0) continue
                    self["past." + name.substringAfter("present.")] = r.get(k) as OnnxTensor
                }
                if (results.size > 2) { val old = results.removeAt(1); old.close() }   // keep the init result (cross cache) and the newest
            }
        } finally {
            results.forEach { it.close() }; hid.close(); inIds.close(); mask.close(); startT.close()
        }
        return seq
    }

    /** One line, as the app translates it (nmt_onnx.translate_scored with the int8 guard). */
    fun translate(text: String, src: String, tgt: String): String {
        val pre = IndicProc.preprocess(text, src, tgt)
        val input = tokenizer.encode(pre.text)
        val limit = NmtGuard.lengthCap(input.size, hardMax = 128)
        val seq = generate(input, limit) { s ->
            val words = NmtGuard.pySplit(tokenizer.decode(s)).dropLast(1)
            NmtGuard.firstLoop(words) != null
        }
        lastSeq = seq
        val out = IndicProc.postprocess(tokenizer.decode(seq), tgt, pre.placeholders)
        val (cut, fired) = NmtGuard.cutStemLoop(out)
        lastCut = fired
        return cut
    }

    override fun close() { enc.close(); init.close(); step.close(); opts.close() }
}
