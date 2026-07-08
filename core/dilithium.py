import oqs
import json

DILITHIUM_ALG = "ML-DSA-44"

def generate_keypair():
    """
    Generate a Dilithium public/private keypair.
    Used by the OTA server to sign update packages.
    Returns (public_key_bytes, private_key_bytes)
    """
    with oqs.Signature(DILITHIUM_ALG) as signer:
        public_key = signer.generate_keypair()
        private_key = signer.export_secret_key()
    return public_key, private_key


def sign(private_key: bytes, message: bytes) -> bytes:
    """
    OTA server side: sign a firmware package payload.
    Returns signature_bytes
    """
    with oqs.Signature(DILITHIUM_ALG, secret_key=private_key) as signer:
        signature = signer.sign(message)
    return signature


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """
    Vehicle side: verify the server's signature on the payload.
    Returns True if signature is valid, False on any failure.
    """
    try:
        with oqs.Signature(DILITHIUM_ALG) as verifier:
            return verifier.verify(message, signature, public_key)
    except Exception:
        return False