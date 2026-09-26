# Oral reading fluency (C1): alignment check on public adult read speech

- FLEURS Hindi, 80 clips, the app's saved Hindi transcripts (CTC, no trimming); no new recognition. Adults reading; **children's reading: NOT MEASURED**.
- (1) Passage = the sentence read: every word should be correct. (2) 10 % of each passage's words replaced (seeded), so exactly those were 'misread': detection precision / recall.

| Matching | Words wrongly marked (1) | Misreadings found: precision / recall (2) |
|---|---|---|
| near spelling | 85 of 1430 (5.9 %) | 0.570 / 1.000 (n = 106) |
| exact | 138 of 1430 (9.7 %) | 0.445 / 1.000 (n = 106) |

- The app uses near-spelling matching (character similarity ≥ 0.75): recognisers spell some correctly read words differently, which exact matching counts as errors.
