"""IndicConformer 120M (Hindi, Santali) -> sherpa-onnx NeMo transducer (RNN-T), fp32 + INT8.

F1 Phase A, for F4 hotwords (sherpa-onnx supports hotwords only on transducers,
docs/sources.md#sherpa-hotwords). Runs where indicconformer_sherpa_export.py runs
(Python 3.10, AI4Bharat NeMo nemo-v2):

    python tools/export/indicconformer_sherpa_export_rnnt.py \
        --nemo hi=models/indicconformer-120m/hi/indicconformer_stt_hi_hybrid_rnnt_large.nemo \
        --nemo sat=models/indicconformer-120m/sat/indicconformer_stt_sat_hybrid_rnnt_large.nemo \
        --clips bench/clips/public/manifest.json --out models/indicconformer-120m-sherpa

**Multisoftmax, as the fork decodes it** (nemo-v2, read from the source):
- the joiner has one output layer PER LANGUAGE (`joint_net[-1][lang]`, 257 outputs:
  256 tokens + blank); hybrid_rnnt_ctc_bpe_models.py sets the RNN-T blank to
  5633 // 22 = 256, a LOCAL index;
- the greedy decoder feeds the emitted LOCAL token id (0..255) back into the
  prediction network's shared embedding, and starts from a zero vector (SOS = blank);
- so the export keeps the encoder as is, the language's own joiner layer, and an
  embedding of rows 0..255 plus a zero blank row.
The export is then checked, not trusted: NeMo's own RNN-T transcripts are saved
for tools/export/compare_nemo_sherpa_rnnt.py.

Writes, per language, into `<out>/<lang>/rnnt/`: encoder/decoder/joiner .onnx and
.int8.onnx (dynamic QUInt8, like sherpa-onnx's own NeMo script), tokens.txt,
bpe.vocab (for hotwords), and nemo_rnnt_transcripts.json.
"""

import argparse
import json
from pathlib import Path

import torch


def parse():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nemo", action="append", required=True, metavar="LANG=PATH")
    ap.add_argument("--clips", type=Path)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--out", type=Path, required=True)
    return ap.parse_args()


def export(lang, nemo_path, a):
    import nemo.collections.asr as nemo_asr
    import onnx
    from onnxruntime.quantization import QuantType, quantize_dynamic

    model = nemo_asr.models.ASRModel.restore_from(str(nemo_path), map_location="cpu")
    model.eval()
    model.preprocessor.featurizer.dither = 0.0
    model.preprocessor.featurizer.pad_to = 0
    cfg = model.cfg
    d = a.out / lang / "rnnt"
    d.mkdir(parents=True, exist_ok=True)

    # NeMo's own RNN-T transcripts first, from the untouched model.
    if a.clips:
        clips = [c for c in json.loads(a.clips.read_text(encoding="utf-8")) if c["lang"] == lang]
        model.cur_decoder = "rnnt"
        with torch.no_grad():
            hyps = model.transcribe([str(a.root / c["file"]) for c in clips], batch_size=1, language_id=lang)
        if isinstance(hyps, tuple):
            hyps = hyps[0]
        hyps = [h.text if hasattr(h, "text") else h for h in hyps]
        (d / "nemo_rnnt_transcripts.json").write_text(json.dumps(
            {c["file"]: h for c, h in zip(clips, hyps)}, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"{lang}: {len(hyps)} NeMo RNN-T transcripts", flush=True)

    tok = model.tokenizer.tokenizers_dict[lang]
    n = tok.vocab_size
    joint, dec = model.joint, model.decoder
    assert getattr(joint, "multilingual", False), "expected the fork's per-language joiner"
    final = joint.joint_net[-1][lang]
    assert final.out_features == n + 1, (final.out_features, n)
    info = {"language": lang, "language_vocab": n, "joiner_final": [final.in_features, final.out_features],
            "embedding_rows_before": dec.prediction["embed"].num_embeddings,
            "pred_hidden": cfg.decoder.prednet.pred_hidden, "pred_rnn_layers": cfg.decoder.prednet.pred_rnn_layers,
            "subsampling_factor": cfg.encoder.get("subsampling_factor")}

    # Joiner: the language's own output layer, no language routing.
    joint.joint_net[-1] = final
    joint.multilingual = False
    joint._vocab_size = n
    joint._num_classes = n + 1
    # Prediction network: local ids 0..n-1 index the shared embedding directly (as the
    # fork's decoder does); blank n is the zero start vector.
    old = dec.prediction["embed"]
    emb = torch.nn.Embedding(n + 1, old.embedding_dim, padding_idx=n)
    with torch.no_grad():
        emb.weight[:n] = old.weight[:n]
        emb.weight[n].zero_()
    dec.prediction["embed"] = emb
    dec.vocab_size = n
    dec.blank_idx = n
    if hasattr(dec, "multisoftmax"):
        dec.multisoftmax = False
    (d / "inspect.json").write_text(json.dumps(info, indent=1, default=str), encoding="utf-8")
    print(json.dumps(info), flush=True)

    model.set_export_config({"decoder_type": "rnnt"})
    model.encoder.export(str(d / "encoder.onnx"))
    dec.export(str(d / "decoder.onnx"))
    # The fork's joiner declares a language_ids input, which NeMo's exporter cannot
    # trace; export the same computation (projection, sum, language layer, log-softmax)
    # through a wrapper with sherpa-onnx's NeMo joiner interface.
    class Joiner(torch.nn.Module):
        def __init__(self, j):
            super().__init__()
            self.j = j

        def forward(self, encoder_outputs, decoder_outputs):      # [B, 512, T], [B, 640, U]
            f = self.j.enc(encoder_outputs.transpose(1, 2))
            g = self.j.pred(decoder_outputs.transpose(1, 2))
            return self.j.joint_after_projection(f, g)          # [B, T, U, n + 1], log-softmax on CPU

    enc_dim = cfg.joint.jointnet.encoder_hidden
    pred_dim = cfg.joint.jointnet.pred_hidden
    with torch.no_grad():
        torch.onnx.export(Joiner(joint).eval(), (torch.randn(1, enc_dim, 1), torch.randn(1, pred_dim, 1)),
                          str(d / "joiner.onnx"), opset_version=17,
                          input_names=["encoder_outputs", "decoder_outputs"], output_names=["outputs"],
                          dynamic_axes={"encoder_outputs": {0: "B", 2: "T"}, "decoder_outputs": {0: "B", 2: "U"},
                                        "outputs": {0: "B", 1: "T", 2: "U"}})

    pieces = [tok.ids_to_tokens([i])[0] for i in range(n)]
    with open(d / "tokens.txt", "w", encoding="utf-8") as f:
        for i, t in enumerate(pieces):
            f.write(f"{t} {i}\n")
        f.write(f"<blk> {n}\n")
    # bpe.vocab for sherpa-onnx hotwords: the sentencepiece vocabulary (piece<TAB>score).
    sp = tok.tokenizer
    with open(d / "bpe.vocab", "w", encoding="utf-8") as f:
        for i in range(sp.get_piece_size()):
            f.write(f"{sp.id_to_piece(i)}\t{sp.get_score(i)}\n")

    m = onnx.load(str(d / "encoder.onnx"))
    meta = {"vocab_size": str(n), "normalize_type": str(cfg.preprocessor.get("normalize") or ""),
            "pred_rnn_layers": str(info["pred_rnn_layers"]), "pred_hidden": str(info["pred_hidden"]),
            "subsampling_factor": str(info["subsampling_factor"]),
            "model_type": "EncDecHybridRNNTCTCBPEModel", "version": "1", "model_author": "AI4Bharat",
            "url": f"https://huggingface.co/ai4bharat/indicconformer_stt_{lang}_hybrid_ctc_rnnt_large",
            "comment": f"RNN-T branch only, joiner and embedding reduced to language '{lang}' (multisoftmax)"}
    for k, v in meta.items():
        p = m.metadata_props.add()
        p.key, p.value = k, v
    onnx.save(m, str(d / "encoder.onnx"))
    for part in ("encoder", "decoder", "joiner"):
        quantize_dynamic(str(d / f"{part}.onnx"), str(d / f"{part}.int8.onnx"), weight_type=QuantType.QUInt8)
    for f in sorted(d.glob("*.onnx")):
        print(f"{lang} {f.name}: {f.stat().st_size / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    a = parse()
    for kv in a.nemo:
        lang, path = kv.split("=", 1)
        export(lang, Path(path), a)
