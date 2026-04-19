"""Dilithium2 helpers for OTA package authenticity checks."""

from __future__ import annotations

import oqs


def _resolve_dilithium_algorithm() -> str:
	"""Resolve to a supported Dilithium2/ML-DSA equivalent mechanism."""
	enabled = set(oqs.get_enabled_sig_mechanisms())
	if "Dilithium2" in enabled:
		return "Dilithium2"
	if "ML-DSA-44" in enabled:
		return "ML-DSA-44"
	raise RuntimeError("No supported Dilithium2/ML-DSA-44 mechanism enabled")


DILITHIUM_ALGORITHM = _resolve_dilithium_algorithm()


def generate_keypair() -> tuple[bytes, bytes]:
	"""Generate Dilithium2 keypair used by OTA servers for signing updates."""
	with oqs.Signature(DILITHIUM_ALGORITHM) as signer:
		public_key = signer.generate_keypair()
		private_key = signer.export_secret_key()
	return public_key, private_key


def sign(private_key: bytes, message: bytes) -> bytes:
	"""Sign OTA payload bytes with the server's Dilithium2 private key."""
	with oqs.Signature(DILITHIUM_ALGORITHM, private_key) as signer:
		signature = signer.sign(message)
	return signature


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
	"""Verify OTA payload signature with Dilithium2 server public key."""
	try:
		with oqs.Signature(DILITHIUM_ALGORITHM) as verifier:
			return verifier.verify(message, signature, public_key)
	except Exception:
		return False
