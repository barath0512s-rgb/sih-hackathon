"""The page the server sends must not load anything from the internet."""

import re

import config

HTML = (config.BASE_DIR / "frontend.html").read_text(encoding="utf-8")

# URLs that appear in the file but are never fetched:
#   the SVG XML namespace inside an inline data: image, and the JS fallback
#   address used when the page is opened straight from disk.
NOT_FETCHED = {"http://www.w3.org/2000/svg", "http://127.0.0.1:5000"}


def test_no_external_urls():
    urls = set(re.findall(r"https?://[^\s'\"()<>%]+", HTML))
    assert urls <= NOT_FETCHED, sorted(urls - NOT_FETCHED)


def test_no_remote_stylesheets_or_scripts():
    assert not re.search(r"<link[^>]+href=[\"']https?:", HTML)
    assert not re.search(r"<script[^>]+src=[\"']https?:", HTML)
    assert "@import" not in HTML


def test_every_font_face_file_exists():
    srcs = re.findall(r"url\('/static/fonts/([^']+)'\)", HTML)
    assert len(srcs) >= 5
    for name in srcs:
        assert (config.STATIC_DIR / "fonts" / name).exists(), name


def test_olchiki_font_is_in_every_text_stack():
    """Ol Chiki must never depend on the device having a system font for it."""
    for var in ("--deva", "--olck"):
        m = re.search(var + r":([^;]+)", HTML)
        assert m and "Noto Sans Ol Chiki" in m.group(1), var


def test_english_is_hidden_unless_evaluator_mode():
    # The teacher's screen has no English; ?evaluator=1 shows the EN button.
    assert re.search(r'<button id="langEn"[^>]*\bhidden\b', HTML)
    assert 'get("evaluator")' in HTML


def test_the_page_runs_on_android_9_webview():
    """Android 9's stock WebView is Chrome 69 (the 2 GB emulator had 69.0.3497):
    no nullish/optional chaining, logical assignment, numeric separators or newer
    built-ins. One of them is a syntax error there and the whole page stops."""
    import re
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / "frontend.html").read_text(encoding="utf-8")
    js = "\n".join(re.findall(r"<script>(.*?)</script>", html, re.S))
    js = re.sub(r"//[^\n]*", "", js)                         # comments may mention them
    banned = {r"\?\?": "??", r"\?\.(?!\d)": "?.", r"(\|\||&&)=": "logical assignment", r"(?<![\w$])\d+_\d": "numeric separator",
              r"\.replaceAll\(": "replaceAll", r"Object\.fromEntries": "Object.fromEntries",
              r"\.matchAll\(": "matchAll", r"allSettled": "Promise.allSettled", r"\.at\(": ".at()",
              r"globalThis": "globalThis", r"structuredClone": "structuredClone", r"Promise\.any": "Promise.any"}
    found = [name for pat, name in banned.items() if re.search(pat, js)]
    assert not found, f"not in Chrome 69: {found}"
