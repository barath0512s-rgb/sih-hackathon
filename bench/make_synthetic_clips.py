"""Make synthetic benchmark clips: Piper reading classroom lines.

These let the latency benchmark run before real recordings exist. They are NOT
real classroom speech: the voice is synthetic and clean, so ASR accuracy on
them says little about accuracy on children or teachers in a noisy room. Use
them for timing only. Real recordings go in bench/clips/real/ (see README there).

Each clip is padded with silence (0.8 s before, 0.6 s after), as a
push-to-talk recording would be, then encoded to WebM/Opus like the browser's
MediaRecorder output, so the server does the same ffmpeg decode as in class.

    python bench/make_synthetic_clips.py        -> bench/clips/synthetic/
"""

import io
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402

OUT = ROOT / "bench" / "clips" / "synthetic"
PAD_BEFORE, PAD_AFTER = 0.8, 0.6

HINDI = [
    "आज हम एक से दस तक गिनना सीखेंगे।", "अपनी उंगलियां दिखाओ और मेरे साथ गिनो।",
    "अब तुम्हारे सामने पांच पत्थर हैं। उन्हें गिनो।", "यहाँ कितने पत्थर हैं? बताओ।",
    "यह गोल है। यह एक वृत्त है।", "यह चौकोर है। इसके चार कोने हैं।",
    "अपने आसपास गोल चीज़ें ढूंढो।", "यह कौन सा आकार है?",
    "आज हम जोड़ना सीखेंगे। एक और एक मिलाओ।", "दो आम और तीन आम मिलाओ। कुल कितने हुए?",
    "अब तुम एक जोड़ का सवाल बनाओ।", "तीन और चार कितने होते हैं?",
    "यह शब्द है माँ। इसे पढ़ो।", "इस शब्द को तीन बार पढ़ो।",
    "यह शब्द क्या है? पढ़कर बताओ।", "आज हम घटाना सीखेंगे। दस में से तीन घटाओ।",
    "सात पत्थर लो। तीन हटा दो। अब कितने बचे?", "आठ में से पांच घटाओ। उत्तर क्या है?",
    "सुप्रभात बच्चों।", "कृपया अपनी जगह पर बैठ जाओ।", "मेरी बात ध्यान से सुनो।",
    "शोर मत करो।", "अपना हाथ उठाओ।", "बहुत अच्छा, शाबाश!",
    "बोर्ड पर आकर लिखो।", "तुम्हारा जवाब बिल्कुल सही है।",
    "यह गलत है, फिर से कोशिश करो।", "अपनी किताब खोलो।",
    "पानी पीकर आओ।", "कल फिर मिलेंगे।",
]


def santali_lines(n):
    """Santali lines from the project's own verified sources."""
    import csv
    import education_glossary as g
    lines = list(g.VERIFIED_SENTENCES_HI_SAT.values())
    with open(ROOT / "training_data" / "nipun_hindi_santali.csv", encoding="utf-8") as f:
        lines += [r["santali"] for r in csv.DictReader(f)]
    seen, out = set(), []
    for s in lines:
        if s not in seen:
            seen.add(s); out.append(s)
    return out[:n]


def synth(voice, text, path):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        voice.synthesize_wav(text, wf)
    buf.seek(0)
    audio, sr = sf.read(buf, dtype="float32")
    audio = np.concatenate([np.zeros(int(PAD_BEFORE * sr), np.float32), audio,
                            np.zeros(int(PAD_AFTER * sr), np.float32)])
    wav = path.with_suffix(".wav")
    sf.write(wav, audio, sr)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                    "-c:a", "libopus", "-b:a", "32k", str(path)], check=True)
    wav.unlink()
    return len(audio) / sr


def main():
    from piper import PiperVoice
    from translit.olchiki import to_devanagari
    voice = PiperVoice.load(str(config.PIPER_DIR / "hi_IN-pratham-medium.onnx"))
    manifest = []
    for lang, lines in (("hi", HINDI), ("sat", santali_lines(len(HINDI)))):
        d = OUT / lang
        d.mkdir(parents=True, exist_ok=True)
        for i, text in enumerate(lines, 1):
            path = d / f"{lang}_{i:02d}.webm"
            spoken = text if lang == "hi" else to_devanagari(text)
            secs = synth(voice, spoken, path)
            manifest.append({"file": path.relative_to(ROOT).as_posix(), "lang": lang,
                             "reference": text, "seconds": round(secs, 2),
                             "kind": "synthetic: Piper hi_IN-pratham-medium, not real speech"})
        print(f"{lang}: {len(lines)} clips in {d.relative_to(ROOT)}")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8")
    print(f"manifest: {len(manifest)} clips")


if __name__ == "__main__":
    main()
