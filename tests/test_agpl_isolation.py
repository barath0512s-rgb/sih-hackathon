"""The AGPL tools (aksharamukha, pymupdf) are dev/test-only: the application
never lists, imports or loads them. No models needed."""

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGPL = {"aksharamukha", "fitz", "pymupdf"}          # fitz is pymupdf's import name

# The application: the server, everything it imports, and the app's packages.
# Tests, benchmarks, evaluation, tools and _archive may use the dev tools.
APP_FILES = sorted(
    [p for p in ROOT.glob("*.py") if p.name not in {"test_pipeline.py", "verify_models.py",
                                                     "train_nmt.py", "generate_dataset.py",
                                                     "download_models.py"}]
    + list((ROOT / "translit").glob("*.py")) + list((ROOT / "nipun").glob("*.py")))


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def test_agpl_tools_are_only_in_requirements_dev():
    for name in ("requirements.txt", "requirements-ci.txt"):
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        for pkg in ("aksharamukha", "pymupdf"):
            assert not any(line.strip().startswith(pkg) for line in text.splitlines()), (name, pkg)
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "aksharamukha==" in dev and "pymupdf==" in dev


def test_no_app_source_imports_them():
    assert APP_FILES and any(p.name == "app.py" for p in APP_FILES)
    for p in APP_FILES:
        bad = AGPL & set(_imports(p))
        assert not bad, f"{p.relative_to(ROOT)} imports {bad}"


def test_app_modules_do_not_load_them():
    # Every app module that loads without the models; then no AGPL module is in memory.
    code = ("import sys; sys.path.insert(0, r'%s')\n"
            "import config, database, textnorm, curriculum, lesson_engine, education_glossary, "
            "worksheet, translit.olchiki, nipun.lakshya, tools.make_cert\n"
            "bad = sorted(m for m in sys.modules if m.split('.')[0] in %r)\n"
            "print(','.join(bad))" % (ROOT, AGPL))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "", f"loaded: {r.stdout.strip()}"
