"""IndicTrans2 translation with ONNX Runtime (Phase L1b; shared with F1).

The same pre- and post-processing as pipeline._nmt (IndicProcessor and the
model's own tokenizer), then a greedy loop over the graphs written by
tools/export/export_indictrans2_onnx.py:
  - no-repeat 3-gram, as the app sets it (config.NMT_NO_REPEAT_NGRAM);
  - the same output-length cap as the app.
The encoder runs once, decoder_init once (it also computes the cross-attention
cache), then decoder_step once per new token with the self-attention cache.
"""

import threading
from pathlib import Path

import numpy as np

import config

ONNX_DIR = config.MODELS_DIR / "indictrans2-onnx"


class OnnxNMT:
    def __init__(self, tokenizer, processor, int8=True, threads=4, onnx_dir=ONNX_DIR, variant=None):
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sfx = f".{variant}.onnx" if variant else (".int8.onnx" if int8 else ".onnx")
        mk = lambda n: ort.InferenceSession(str(Path(onnx_dir) / f"{n}{sfx}"), so, providers=["CPUExecutionProvider"])
        self.enc, self.init, self.step = mk("encoder"), mk("decoder_init"), mk("decoder_step")
        self.tok, self.ip = tokenizer, processor
        self.n_layers = sum(1 for o in self.step.get_outputs() if o.name.endswith(".self_k"))
        # The exporter drops inputs a graph does not use (decoder_step takes its
        # cross-attention keys from the cache, not encoder_hidden_states).
        self.step_inputs = {i.name for i in self.step.get_inputs()}
        self.start, self.eos = 2, 2
        self.lock = threading.Lock()        # the IndicProcessor queue is per instance

    @staticmethod
    def _banned(tokens, n):
        """Tokens that would repeat an n-gram already generated (HF no_repeat_ngram_size)."""
        if len(tokens) < n:
            return set()
        prefix = tuple(tokens[-(n - 1):])
        return {tokens[i + n - 1] for i in range(len(tokens) - n + 1) if tuple(tokens[i:i + n - 1]) == prefix}

    def generate_ids(self, input_ids, attention_mask, max_new_tokens, logps=None):
        hid = self.enc.run(None, {"input_ids": input_ids, "attention_mask": attention_mask})[0]
        out = self.init.run(None, {"decoder_input_ids": np.array([[self.start]], dtype=np.int64),
                                   "encoder_hidden_states": hid, "encoder_attention_mask": attention_mask})
        logits, pres = out[0], out[1:]
        self_kv = [pres[4 * i:4 * i + 2] for i in range(self.n_layers)]
        cross_kv = [pres[4 * i + 2:4 * i + 4] for i in range(self.n_layers)]
        seq = [self.start]
        for _ in range(max_new_tokens):
            scores = logits[0, -1].astype(np.float32)
            for b in self._banned(seq, config.NMT_NO_REPEAT_NGRAM):
                scores[b] = -np.inf
            nxt = int(scores.argmax())
            if logps is not None:
                # The same as HF compute_transition_scores(normalize_logits=True):
                # log-softmax of the processed scores, at the chosen token.
                finite = scores[np.isfinite(scores)]
                m = finite.max()
                logps.append(float(scores[nxt] - m - np.log(np.exp(finite - m).sum())))
            seq.append(nxt)
            if nxt == self.eos:
                break
            feed = {"decoder_input_ids": np.array([[nxt]], dtype=np.int64),
                    "encoder_hidden_states": hid, "encoder_attention_mask": attention_mask}
            for i in range(self.n_layers):
                feed[f"past.{i}.self_k"], feed[f"past.{i}.self_v"] = self_kv[i]
                feed[f"past.{i}.cross_k"], feed[f"past.{i}.cross_v"] = cross_kv[i]
            out = self.step.run(None, {k: v for k, v in feed.items() if k in self.step_inputs})
            logits = out[0]
            self_kv = [out[1 + 2 * i:3 + 2 * i] for i in range(self.n_layers)]
        return seq

    def translate(self, text, src_lang, tgt_lang):
        out, seq, _ = self.translate_scored(text, src_lang, tgt_lang)
        return out, seq

    def translate_scored(self, text, src_lang, tgt_lang):
        """(text, token ids, model_score): model_score as in pipeline._nmt."""
        with self.lock:
            batch = self.ip.preprocess_batch([text], src_lang=src_lang, tgt_lang=tgt_lang)
            enc = self.tok(batch, truncation=True, padding="longest", return_tensors="np")
            ids = enc["input_ids"].astype(np.int64)
            mask = enc["attention_mask"].astype(np.int64)
            limit = min(config.NMT_MAX_TOKENS, config.NMT_LIMIT_FACTOR * ids.shape[1] + config.NMT_LIMIT_MARGIN)
            logps = []
            seq = self.generate_ids(ids, mask, limit, logps)
            dec = self.tok.batch_decode([seq], skip_special_tokens=True, clean_up_tokenization_spaces=True)
            score = round(float(np.exp(np.mean(logps))), 3) if logps else None
            return self.ip.postprocess_batch(dec, lang=tgt_lang)[0], seq, score
