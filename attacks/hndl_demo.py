"""Harvest-now-decrypt-later comparison between RSA and Kyber encapsulation."""

from __future__ import annotations

import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from core import kyber


def run_hndl_demo() -> dict:
	"""Return side-by-side metadata comparing classical RSA and Kyber ciphertexts."""
	rsa_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	rsa_public_key = rsa_private_key.public_key()

	fake_session_key = os.urandom(32)
	classical_ciphertext = rsa_public_key.encrypt(
		fake_session_key,
		padding.OAEP(
			mgf=padding.MGF1(algorithm=hashes.SHA256()),
			algorithm=hashes.SHA256(),
			label=None,
		),
	)

	kyber_public_key, _ = kyber.generate_keypair()
	pq_ciphertext, _ = kyber.encapsulate(kyber_public_key)

	return {
		"classical": {
			"algorithm": "RSA-2048",
			"ciphertext_size": len(classical_ciphertext),
			"quantum_safe": False,
		},
		"post_quantum": {
			"algorithm": "Kyber512",
			"ciphertext_size": len(pq_ciphertext),
			"quantum_safe": True,
		},
		"verdict": "RSA ciphertext is vulnerable to future quantum decryption. Kyber is not.",
	}
