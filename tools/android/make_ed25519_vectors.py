"""Write tests/data/ed25519_vectors.json: what Ed25519.kt must reproduce (A4).

    python tools/android/make_ed25519_vectors.py

RFC 8032 section 7.1 TEST 1 (checked against Python's `cryptography` here), plus
signatures made by `cryptography` for fixed seeds and messages, including a
tablet-export-like payload. Ed25519 is deterministic, so the Kotlin port must
produce the same signatures byte for byte: then the hub (Python) verifies what
the tablet signs, and the tablet verifies what the hub signs.
"""
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tests" / "data" / "ed25519_vectors.json"
RFC_TEST1 = {"seed": "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
             "public": "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "message": "",
             "signature": "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"}


def sign(seed_hex, msg: bytes):
    k = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))
    pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    return pub, k.sign(msg).hex()


def build():
    pub, sig = sign(RFC_TEST1["seed"], b"")
    assert (pub, sig) == (RFC_TEST1["public"], RFC_TEST1["signature"]), "cryptography disagrees with RFC 8032"
    vectors = [dict(RFC_TEST1, source="RFC 8032 7.1 TEST 1")]
    msgs = ["नमस्ते ᱡᱚᱦᱟᱨ", '{"format":1,"kind":"tablet-export","corrections":[]}', "x" * 1000]
    for i, m in enumerate(msgs):
        seed = hashlib.sha256(f"nijbhasha-test-{i}".encode()).hexdigest()
        pub, sig = sign(seed, m.encode("utf-8"))
        vectors.append({"seed": seed, "public": pub, "message": m.encode("utf-8").hex(), "signature": sig,
                        "source": "cryptography"})
    vectors[0]["message"] = ""
    return json.dumps({"note": __doc__.split("\n\n")[0], "vectors": vectors}, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print("wrote", OUT.relative_to(ROOT))
