"""Markdown summary of a pytest JUnit report, for the GitHub run page (no login needed)."""
import sys
import xml.etree.ElementTree as ET

WATCH = ["test_the_page_runs_on_android_9_webview", "test_the_android_test_pack_is_intact",
         "test_a_flagged_reply_is_never_auto_played", "test_every_claim_number_is_in_its_own_evidence_file"]

root = ET.parse(sys.argv[1]).getroot()
suites = [root] if root.tag == "testsuite" else list(root)
cases = [c for s in suites for c in s.iter("testcase")]
state = lambda c: ("failed" if c.find("failure") is not None or c.find("error") is not None
                   else "skipped" if c.find("skipped") is not None else "passed")
counts = {}
for c in cases:
    counts[state(c)] = counts.get(state(c), 0) + 1
print("### Tests (no model weights in CI)")
print("")
print(", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
print("")
print("| Watched test | Result |")
print("|---|---|")
for name in WATCH:
    hit = [c for c in cases if c.get("name") == name]
    print(f"| `{name}` | {state(hit[0]) if hit else 'NOT FOUND'} |")
