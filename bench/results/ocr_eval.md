# Photo import (C2): character accuracy on the team's ten test pages

- Pages: `docs/samples/ocr_pages/` (the team's own Hindi; printed text in `page_NN.txt`). OCR: Tesseract with `hin.traineddata` on the laptop hub (`ocr.py`). CER after NFC and collapsing whitespace.

- **Phone photos of the printed pages**: **NOT MEASURED** (no photos in data/ocr_photos/ yet).
- Rendered PDF images (clean upper bound, not photos): 10 pages, **CER mean 5.0 %**, median 5.2 %; lines read exactly: 28 of 79.

| Page | Photo CER | Rendered CER |
|---|---|---|
| page_01 | — | 7.9 % |
| page_02 | — | 2.1 % |
| page_03 | — | 8.8 % |
| page_04 | — | 5.8 % |
| page_05 | — | 3.3 % |
| page_06 | — | 3.4 % |
| page_07 | — | 5.7 % |
| page_08 | — | 5.7 % |
| page_09 | — | 4.7 % |
| page_10 | — | 3.0 % |
