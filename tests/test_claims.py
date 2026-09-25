"""The fact-check protocol: docs/claims.yaml is complete and every README number
has evidence (no models needed)."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CLAIMS = yaml.safe_load((ROOT / "docs" / "claims.yaml").read_text(encoding="utf-8"))
STATUSES = {"TRUE", "FALSE", "NOT MEASURED", "NOT BUILT"}


def _evidence_files():
    return sorted({(ROOT / c["evidence"].split("#")[0]) for c in CLAIMS})


def test_every_claim_is_well_formed():
    ids = [c["id"] for c in CLAIMS]
    assert len(ids) == len(set(ids)), "duplicate claim ids"
    for c in CLAIMS:
        assert set(c) >= {"id", "text", "status", "evidence"}, c
        assert c["status"] in STATUSES, c


def test_every_evidence_exists_including_anchors():
    sources = (ROOT / "docs" / "sources.md").read_text(encoding="utf-8")
    anchors = set(re.findall(r'<a name="([^"]+)"></a>', sources))
    for c in CLAIMS:
        path, _, anchor = c["evidence"].partition("#")
        assert (ROOT / path).exists(), f"{c['id']}: {path} missing"
        if anchor:
            assert path == "docs/sources.md" and anchor in anchors, f"{c['id']}: #{anchor} not in sources.md"


def readme_numbers():
    s = (ROOT / "README.md").read_text(encoding="utf-8")
    s = re.sub(r"```.*?```", " ", s, flags=re.S)           # code blocks
    s = re.sub(r"`[^`]*`", " ", s)                          # inline code: paths, IDs, commands
    s = re.sub(r"\((?:https?|mailto):[^)]*\)|https?://\S+", " ", s)
    s = re.sub(r"^#+ .*$", " ", s, flags=re.M)              # section headings ("## 6.")
    s = re.sub(r"^\s*(\d+[a-z]?)\.\s", " ", s, flags=re.M)  # numbered-list markers
    s = re.sub(r"\b[A-Z][A-Z0-9]*-[A-Z0-9-]+\b", " ", s)    # identifiers like NIPUN-G1-NUM-2, SIH26042
    s = re.sub(r"\bSIH\d+\b|§\s?\d+", " ", s)
    # ASCII digits only: "(7, ७, ᱗)" shows digit scripts, it is not a claim.
    toks = re.findall(r"(?<![\w.])[0-9][0-9,]*(?:\.[0-9]+)?", s)
    return sorted({t.rstrip(",.") for t in toks if t.rstrip(",.")})


def test_every_readme_number_has_evidence():
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in _evidence_files()
                     if p.is_file())
    flat = text.replace(",", "")
    missing = [n for n in readme_numbers() if n not in text and n.replace(",", "") not in flat]
    assert not missing, (f"README numbers with no evidence file in docs/claims.yaml: {missing}. "
                         "Add the source to docs/sources.md or a results file, or remove the number.")


def test_every_claim_number_is_in_its_own_evidence_file():
    """A decimal number in a claim (31.3, 2.61) must appear in the file that
    claim cites, not just somewhere in the repo: a number copied from the wrong
    row or run fails here. Percentages are also checked as fractions (31.3% is
    0.313 in a results table)."""
    bad = []
    for c in CLAIMS:
        path = ROOT / c["evidence"].split("#")[0]
        if not path.is_file():
            continue
        ev = path.read_text(encoding="utf-8", errors="replace").replace(",", "")
        for n in re.findall(r"(?<![\w.])\d+\.\d+", c["text"]):
            frac = f"{float(n) / 100:.3f}"
            if n not in ev and frac not in ev and f"{float(n):g}" not in ev:
                bad.append(f"{c['id']}: {n} not in {c['evidence']}")
    assert not bad, "\n".join(bad)
