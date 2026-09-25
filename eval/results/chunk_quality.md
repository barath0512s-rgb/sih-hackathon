# Clause streaming vs whole-sentence translation (Hindi → Santali)

- FLORES-200 devtest (`facebook/flores` @ 71abf77d8b, CC BY-SA 4.0): the 814 of 1012 Hindi sentences with 18+ words (the ones the app streams); n = 814, n_distinct = 814 (FLORES devtest has no repeated source sentence: eval/results/benchmarks.md).
- Engine: onnx-fp32; chunks from `streaming.chunks()`, median 4 per sentence; chunk translations joined with spaces.
- Text input (no speech recognition). Laptop, offline.

| Translation | chrF++ | BLEU |
|---|---|---|
| Whole sentence | 27.5 | 3.4 |
| Chunked (streaming) | 27.3 | 2.3 |

Difference, chunked minus whole: chrF++ -0.2. Chunking scores higher on 387 of 814 sentences. Chunked vs whole agreement: chrF++ 68.5.
