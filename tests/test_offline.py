"""The whole speech path works with the network unplugged.

Sockets are blocked before the pipeline is even imported, so model loading is
proven offline too. The TTS cache points at an empty folder, so every clip is
really synthesised by Piper rather than replayed from an old cache entry.
Needs the model files (python download_models.py); skipped without them.
"""

import socket

import numpy as np
import pytest
import soundfile as sf

import config

pytestmark = pytest.mark.skipif(
    not (config.ASR_DIR / "model_onnx.py").exists() or
    not (config.NMT_DIR / "config.json").exists(),
    reason="model files not downloaded")

SILENCE_RMS = 1e-3


class _NetworkBlocked(OSError):
    pass


def _refuse(*a, **k):
    raise _NetworkBlocked("network access attempted during an offline test")


@pytest.fixture(scope="module")
def offline_pipeline(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    # Only network sockets are refused. Local socketpairs (used internally by
    # some libraries on Windows) are still allowed.
    real_socket = socket.socket

    class GuardedSocket(real_socket):
        def connect(self, *a, **k):
            _refuse()

        def connect_ex(self, *a, **k):
            _refuse()

    mp.setattr(socket, "socket", GuardedSocket)
    mp.setattr(socket, "create_connection", _refuse)
    mp.setattr(socket, "getaddrinfo", _refuse)
    mp.setattr(config, "TTS_CACHE_DIR", tmp_path_factory.mktemp("tts_cache"))
    mp.setattr(config, "ALLOW_ONLINE_TTS", False)

    import pipeline
    pl = pipeline.VaaniSetuPipeline()
    yield pl
    mp.undo()


def _rms(path):
    data, sr = sf.read(path, dtype="float32")
    return float(np.sqrt(np.mean(np.square(data)))), len(data) / sr


def test_the_network_is_really_blocked(offline_pipeline):
    """Guards against a vacuous offline test: real network calls must fail here."""
    import urllib.request
    with pytest.raises(OSError):
        socket.create_connection(("huggingface.co", 443), timeout=3)
    with pytest.raises(OSError):
        urllib.request.urlopen("https://translate.google.com", timeout=3)


def test_hindi_text_to_santali_speech(offline_pipeline, tmp_path):
    pl = offline_pipeline
    sat, _, _ = pl.hindi_to_santali("आज हम जोड़ना सीखेंगे। एक और एक मिलाओ।", "lesson_script")
    out = tmp_path / "sat.wav"
    pl.santali_tts(sat, str(out))
    rms, secs = _rms(out)
    assert rms > SILENCE_RMS and secs > 0.5, (rms, secs)


def test_santali_numbers_are_spoken(offline_pipeline, tmp_path):
    """Numbers inside Santali must produce sound: the old path dropped digits."""
    pl = offline_pipeline
    with_number = "᱗ ᱜᱚᱴᱟᱝ ᱫᱷᱤᱨᱤ"                         # "7 stones", Ol Chiki digit
    assert pl.transliterate_santali(with_number).startswith("एयाय्"), \
        "the digit was not turned into the Santali word for seven"
    out_digits = tmp_path / "digits.wav"
    pl.santali_tts(with_number, str(out_digits))
    rms, secs = _rms(out_digits)
    assert rms > SILENCE_RMS, rms
    out_word = tmp_path / "word.wav"
    pl.santali_tts("ᱜᱚᱴᱟᱝ ᱫᱷᱤᱨᱤ", str(out_word))
    _, secs_without = _rms(out_word)
    # The old path dropped the digit, adding exactly nothing. A spoken
    # two-syllable word adds well over a tenth of a second.
    assert secs > secs_without + 0.1, (secs, secs_without)


def test_santali_text_to_hindi_speech(offline_pipeline, tmp_path):
    pl = offline_pipeline
    hi = pl.santali_to_hindi("ᱟᱢ ᱟᱢᱟᱜ ᱚᱛᱟᱭ ᱨᱮ ᱦᱮᱡ ᱢᱮ")
    assert any("ऀ" <= c <= "ॿ" for c in hi), hi
    out = tmp_path / "hi.wav"
    pl.hindi_tts(hi, str(out))
    rms, secs = _rms(out)
    assert rms > SILENCE_RMS and secs > 0.5, (rms, secs)


def test_no_online_engine_was_used(offline_pipeline):
    counts = offline_pipeline.tts_engine_counts
    assert counts["gtts"] == 0
    assert counts["piper"] >= 3


def test_missing_voice_raises_instead_of_writing_silence(offline_pipeline, tmp_path, monkeypatch):
    import pipeline
    monkeypatch.setitem(config.PIPER_VOICES, "hindi", "no-such-voice")
    out = tmp_path / "none.wav"
    with pytest.raises(pipeline.TTSError):
        offline_pipeline.hindi_tts("नमस्ते", str(out))
    assert not out.exists()
