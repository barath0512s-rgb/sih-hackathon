"""Ed25519 signatures for content and model packs (A4).

The hub signs manifest.json of every pack it builds; the tablet verifies it with
the public key it ships with (android/app/src/main/assets/pack_signing.pub) and
refuses a pack whose signature is missing or wrong. The manifest already holds
the SHA-256 of every other file, so the signature covers the whole pack.

The private key is made on the hub the first time it is needed and stays there
(certs/pack_signing_ed25519.key, git-ignored like the rest of certs/). A new key
means every tablet needs the new public key (a new app build): keep a copy.
"""

from pathlib import Path

import config

KEY_FILE = config.CERT_DIR / "pack_signing_ed25519.key"
PUB_ASSET = config.BASE_DIR / "android" / "app" / "src" / "main" / "assets" / "pack_signing.pub"
SIG_NAME = "manifest.sig"


def _private():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if KEY_FILE.exists():
        return serialization.load_pem_private_key(KEY_FILE.read_bytes(), password=None)
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    k = Ed25519PrivateKey.generate()
    KEY_FILE.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    return k


def public_hex():
    from cryptography.hazmat.primitives import serialization
    return _private().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def sign_dir(pack_dir):
    """Write <pack>/manifest.sig: hex Ed25519 signature of manifest.json's bytes."""
    d = Path(pack_dir)
    sig = _private().sign((d / "manifest.json").read_bytes())
    (d / SIG_NAME).write_text(sig.hex() + "\n", encoding="ascii", newline="\n")
    return sig.hex()


def verify(public_hex_, data: bytes, sig_hex: str) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex_)).verify(bytes.fromhex(sig_hex.strip()), data)
        return True
    except (InvalidSignature, ValueError):
        return False


def write_public_asset():
    PUB_ASSET.write_text(public_hex() + "\n", encoding="ascii", newline="\n")
    return PUB_ASSET


if __name__ == "__main__":
    print("public key:", write_public_asset().read_text().strip())
