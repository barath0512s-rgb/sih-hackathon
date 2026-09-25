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
| flores (CC BY-SA 4.0) | hin_Deva-sat_Olck | 1012 | 27.4 | 3.3 | 26.1 | 695 s |
| flores (CC BY-SA 4.0) | sat_Olck-hin_Deva | 1012 | 34.1 | 12.6 | 31.5 | 575 s |
| in22-conv (CC BY 4.0) | hin_Deva-sat_Olck | 1503 | 32.2 | 5.5 | 30.4 | 475 s |
| in22-conv (CC BY 4.0) | sat_Olck-hin_Deva | 1503 | 35.1 | 15.3 | 33.8 | 382 s |
| in22-gen (CC BY 4.0) | hin_Deva-sat_Olck | 1024 | 31.3 | 4.2 | 30.0 | 812 s |
| in22-gen (CC BY 4.0) | sat_Olck-hin_Deva | 1024 | 37.6 | 15.8 | 35.8 | 649 s |
