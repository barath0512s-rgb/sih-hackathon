"""Does clause streaming cost translation quality? chrF++ against human references.

    python eval/chunk_quality.py

The app streams Hindi utterances of config.STREAM_MIN_WORDS words or more: it
cuts them with streaming.chunks() and translates chunk by chunk. Here every
FLORES-200 devtest Hindi sentence of that length is translated both ways (whole,
and chunked then joined with spaces), with the app's engine, and both are
scored against the human Santali reference: corpus chrF++ and BLEU, plus how
often chunking wins per sentence. Text input (no speech recognition), laptop.
Writes eval/results/chunk_quality.md. Translations are not saved (the test
set's terms). Evaluation only; never tune on these sentences.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.eval_benchmarks import RESULTS, SETS, load  # noqa: E402


def main():
    import sacrebleu
    pairs, rev = load("flores")
    os.environ["HF_HUB_OFFLINE"] = "1"
    import config
    import pipeline
    import streaming
    pl = pipeline.VaaniSetuPipeline()
    long_ = [(h, s) for h, s in pairs if len(h.split()) >= config.STREAM_MIN_WORDS]
    whole, chunked, refs, n_chunks, wins = [], [], [], [], 0
    for i, (h, s) in enumerate(long_):
        w = pl._apply_domain_glossary(pl._nmt(h, "hin_Deva", "sat_Olck")[0], "sat_Olck")
        parts = streaming.chunks(h)
        c = " ".join(pl._apply_domain_glossary(pl._nmt(p, "hin_Deva", "sat_Olck")[0], "sat_Olck") for p in parts)
        whole.append(w); chunked.append(c); refs.append(s); n_chunks.append(len(parts))
        sw = sacrebleu.sentence_chrf(w, [s], word_order=2).score
        sc = sacrebleu.sentence_chrf(c, [s], word_order=2).score
        wins += sc > sw
        print(f"{i + 1:>4}/{len(long_)} {len(h.split()):>2}w {len(parts)}c  whole {sw:5.1f}  chunked {sc:5.1f}",
              flush=True)
    cw = sacrebleu.corpus_chrf(whole, [refs], word_order=2).score
    cc = sacrebleu.corpus_chrf(chunked, [refs], word_order=2).score
    bw = sacrebleu.corpus_bleu(whole, [refs]).score
    bc = sacrebleu.corpus_bleu(chunked, [refs]).score
    agree = sacrebleu.corpus_chrf(chunked, [whole], word_order=2).score
    lines = ["# Clause streaming vs whole-sentence translation (Hindi → Santali)", "",
             f"- FLORES-200 devtest (`{SETS['flores']['repo']}` @ {rev[:10]}, {SETS['flores']['license']}): "
             f"the {len(long_)} of {len(pairs)} Hindi sentences with {config.STREAM_MIN_WORDS}+ words "
             f"(the ones the app streams); n = {len(long_)}, n_distinct = {len({h for h, _ in long_})}.",
             f"- Engine: {pl.nmt_backend}; chunks from `streaming.chunks()`, median "
             f"{sorted(n_chunks)[len(n_chunks) // 2]} per sentence; chunk translations joined with spaces.",
             "- Text input (no speech recognition). Laptop, offline.", "",
             "| Translation | chrF++ | BLEU |", "|---|---|---|",
             f"| Whole sentence | {cw:.1f} | {bw:.1f} |",
             f"| Chunked (streaming) | {cc:.1f} | {bc:.1f} |", "",
             f"Difference, chunked minus whole: chrF++ {cc - cw:+.1f}. Chunking scores higher on "
             f"{wins} of {len(long_)} sentences. Chunked vs whole agreement: chrF++ {agree:.1f}."]
    (RESULTS / "chunk_quality.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
