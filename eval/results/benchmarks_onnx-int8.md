# Translation benchmark: Hindi <-> Santali

- Date: 2026-09-25; model ai4bharat/indictrans2-indic-indic-dist-320M @ ffb7582b6d, greedy (beams=1);
  the model alone (no teacher corrections, glossary or cache). Laptop, offline.
- chrF++ = sacrebleu corpus_chrf(word_order=2); BLEU = sacrebleu corpus_bleu (13a).
- **Paper column:** IndicTrans2 paper (arXiv 2305.16307v3, Tables 19-21), IT2-Dist-M2M, chrF++
  averaged over ALL Indic languages into Santali (for hin→sat) or from Santali (for sat→hin).
  It is not the Hindi pair itself: a plausibility range, not a like-for-like comparison.
- These test sets are for evaluation only. eval/test_set_hashes.json lets training scripts
  refuse any of their sentences (eval/leakage.py).

| Test set | Direction | n | chrF++ | BLEU | Paper chrF++ (all-source avg) | Time |
|---|---|---|---|---|---|---|
| in22-conv (CC BY 4.0) | hin_Deva-sat_Olck | 1503 | 32.0 | 5.3 | 30.4 | 220 s |
| in22-conv (CC BY 4.0) | sat_Olck-hin_Deva | 1503 | 35.0 | 15.6 | 33.8 | 172 s |
