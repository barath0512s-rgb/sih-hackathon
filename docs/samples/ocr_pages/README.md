# OCR test pages (C2)

Ten pages of the team's own Hindi (lessons in `content/team_lessons.json`, passages in
`content/orf_passages.json`); `page_NN.txt` is the exact text of `page_NN.pdf`.

To test photo import:
1. Print the ten PDFs (A4, black and white is fine).
2. Photograph each page with a phone: the whole page in the frame, in daylight or a lit room,
   held roughly straight (no need to be perfect: that is what is being tested).
3. Save the photos as `data/ocr_photos/page_01.jpg` … `page_10.jpg` on the laptop (not in git).
4. Run `python bench/ocr_eval.py`: character error rate per page, in `bench/results/ocr_eval.md`.
