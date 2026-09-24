"""Is the NMT model score meaningful enough to show teachers? Re-runnable check.

The score is the geometric mean of the per-token probabilities of the greedy
translation (pipeline._nmt). If it were a usable quality signal, well-formed
classroom Hindi would score clearly above gibberish. This prints both groups.

Result when first run (2026-09-24): gibberish scored inside the range of real
sentences (Latin gibberish 0.647 vs a real lesson line 0.619), so the UI does
not show the score. Re-run after changing the model or decoding settings.

    python eval/model_score_sanity.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REAL = [
    "आज हम जोड़ना सीखेंगे।",
    "बच्चे स्कूल जा रहे हैं।",
    "शिक्षक ने कहा कि परीक्षा अगले सोमवार को होगी।",
    "दो आम और तीन आम मिलाओ।",
    "अपनी उंगलियां दिखाओ और मेरे साथ गिनो।",
    "यहाँ कितने पत्थर हैं?",
]
GIBBERISH = [
    "क्लक्ष ग्रमफ़ ट्रुंठ झपक्स।",
    "asdf qwerty zxcv",
    "ठठठ ढढढ णणण",
    "पत्थर पत्थर पत्थर पत्थर पत्थर",
]


def main():
    import config
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    from IndicTransToolkit.processor import IndicProcessor
    import pipeline

    pl = pipeline.VaaniSetuPipeline.__new__(pipeline.VaaniSetuPipeline)
    pl.tok_nmt = AutoTokenizer.from_pretrained(str(config.NMT_DIR), trust_remote_code=True)
    pl.mdl_nmt = AutoModelForSeq2SeqLM.from_pretrained(str(config.NMT_DIR), trust_remote_code=True).eval()
    pl.ip = IndicProcessor(inference=True)

    def scores(lines):
        return [pl._nmt(s, "hin_Deva", "sat_Olck", pl.tok_nmt, pl.mdl_nmt)[1] for s in lines]

    real, junk = scores(REAL), scores(GIBBERISH)
    for s, v in zip(REAL, real):
        print(f"  real       {v:.3f}  {s}")
    for s, v in zip(GIBBERISH, junk):
        print(f"  gibberish  {v:.3f}  {s}")
    overlap = max(junk) >= min(real)
    print(f"\nreal: {min(real):.3f}-{max(real):.3f}   gibberish: {min(junk):.3f}-{max(junk):.3f}")
    print("The ranges OVERLAP: the score does not separate good input from bad. "
          "Do not show it as confidence." if overlap else
          "The ranges are separated on this sample. Validate on a larger set before showing it.")


if __name__ == "__main__":
    main()
