"""Kyber512 helpers for session key establishment in OTA updates."""

from __future__ import annotations

import oqs


def _resolve_kyber_algorithm() -> str:
	"""Resolve to a supported Kyber/ML-KEM algorithm at runtime."""
	enabled = set(oqs.get_enabled_kem_mechanisms())
	if "Kyber512" in enabled:
		return "Kyber512"
	if "ML-KEM-512" in enabled:
		return "ML-KEM-512"
	raise RuntimeError("No supported Kyber512/ML-KEM-512 mechanism enabled")


KYBER_ALGORITHM = _resolve_kyber_algorithm()


def generate_keypair() -> tuple[bytes, bytes]:
	"""Generate a Kyber512 keypair for a vehicle endpoint."""
	with oqs.KeyEncapsulation(KYBER_ALGORITHM) as kem:
		public_key = kem.generate_keypair()
		private_key = kem.export_secret_key()
	return public_key, private_key


def encapsulate(public_key: bytes) -> tuple[bytes, bytes]:
	"""Encapsulate a fresh session key to a vehicle's Kyber public key."""
	with oqs.KeyEncapsulation(KYBER_ALGORITHM) as kem:
		ciphertext, session_key = kem.encap_secret(public_key)
	return ciphertext, session_key


def decapsulate(private_key: bytes, ciphertext: bytes) -> bytes:
	"""Decapsulate a session key from ciphertext using vehicle private key."""
	with oqs.KeyEncapsulation(KYBER_ALGORITHM, private_key) as kem:
		session_key = kem.decap_secret(ciphertext)
	return session_key


def verify_session(private_key: bytes, ciphertext: bytes, expected_key: bytes) -> bool:
	"""Verify that decapsulation reproduces the expected session key."""
	try:
		recovered = decapsulate(private_key, ciphertext)
		return recovered == expected_key
	except Exception:
		return False
