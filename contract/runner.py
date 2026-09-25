"""Run contract/rest_contract.json against any server.

    from contract.runner import run
    failures = run(send, engines={"asr", "nmt", "tts"})

`send(method, path, json_body)` returns (status, content_type, body_bytes). The
Flask test passes the test client (tests/test_contract.py); the device check
passes plain HTTP to the phone through `adb forward` (tools/android/device_contract.py).
`engines`: what this server can run beyond its content pack. A case that needs
a missing engine must be refused with 503 and code "engine_not_on_device".
Returns a list of failure messages (empty = the server meets the contract).
"""

import json
import re
from pathlib import Path

CONTRACT = Path(__file__).resolve().parent / "rest_contract.json"
_TYPES = {"str": str, "int": int, "num": (int, float), "bool": bool, "list": list, "dict": dict, "null": type(None)}


def _get(obj, dotted):
    for part in dotted.split("."):
        if isinstance(obj, list):
            obj = obj[int(part)]
        else:
            obj = obj[part]
    return obj


def _fill(value, saved):
    if isinstance(value, str):
        m = re.fullmatch(r"\{(\w+)\}", value)
        if m:
            return saved[m.group(1)]
        return re.sub(r"\{(\w+)\}", lambda m: str(saved[m.group(1)]), value)
    if isinstance(value, dict):
        return {k: _fill(v, saved) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill(v, saved) for v in value]
    return value


def _type_ok(value, spec):
    for t in spec.split("|"):
        py = _TYPES[t]
        if t in ("int", "num") and isinstance(value, bool):
            continue
        if isinstance(value, py):
            return True
    return False


def load():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def run(send, engines=frozenset({"asr", "nmt", "tts"}), contract=None):
    c = contract or load()
    saved, failures = {}, []
    for case in c["setup"] + c["cases"]:
        cid = case["id"]
        try:
            body = _fill(case.get("json"), saved)
            path = _fill(case["path"], saved)
        except KeyError as e:
            failures.append(f"{cid}: needs {e} from an earlier case")
            continue
        status, ctype, raw = send(case["method"], path, body)
        missing = [e for e in case.get("needs", []) if e not in engines]
        if missing:
            j = _json(raw)
            if status != 503 or not isinstance(j, dict) or j.get("code") != "engine_not_on_device":
                failures.append(f"{cid}: needs {missing}, so expected 503 engine_not_on_device, got {status} {raw[:120]!r}")
            continue
        want = case.get("status", 200)
        if status != want:
            failures.append(f"{cid}: status {status}, expected {want}: {raw[:160]!r}")
            continue
        if "content_type" in case:
            if not (ctype or "").startswith(case["content_type"]):
                failures.append(f"{cid}: content type {ctype}, expected {case['content_type']}")
            continue
        j = _json(raw)
        if not isinstance(j, dict):
            failures.append(f"{cid}: not a JSON object: {raw[:120]!r}")
            continue
        for key, spec in case.get("types", {}).items():
            try:
                v = _get(j, key)
            except (KeyError, IndexError, TypeError, ValueError):
                failures.append(f"{cid}: missing {key}")
                continue
            if not _type_ok(v, spec):
                failures.append(f"{cid}: {key} is {type(v).__name__}, expected {spec}")
        for key, want_v in case.get("equals", {}).items():
            try:
                if _get(j, key) != want_v:
                    failures.append(f"{cid}: {key} = {_get(j, key)!r}, expected {want_v!r}")
            except (KeyError, IndexError, TypeError):
                failures.append(f"{cid}: missing {key}")
        for name, key in case.get("save", {}).items():
            try:
                saved[name] = _get(j, key)
            except (KeyError, IndexError, TypeError, ValueError):
                failures.append(f"{cid}: cannot save {name} from {key}")
    return failures


def _json(raw):
    try:
        return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    except (ValueError, UnicodeDecodeError):
        return None
