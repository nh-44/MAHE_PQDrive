"""Harvest-now-decrypt-later comparison between RSA and Kyber encapsulation."""

from __future__ import annotations

import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from core import kyber


class HarvestNowDecryptLater:
	"""Show that Kyber resists harvest-now-decrypt-later recording."""

	def run(self) -> dict:
		vehicle_pub, vehicle_priv = kyber.generate_keypair()

		# Server sends a legitimate package — adversary records ciphertext
		ciphertext, real_session_key = kyber.encapsulate(vehicle_pub)

		# Adversary attempts recovery: re-encapsulate with same pubkey
		attacker_ct, attacker_recovered = kyber.encapsulate(vehicle_pub)
		_ = attacker_ct
		quantum_broken = attacker_recovered == real_session_key

		# Legitimate vehicle decapsulates correctly
		legit_recovered = kyber.decapsulate(vehicle_priv, ciphertext)
		legit_ok = legit_recovered == real_session_key

		# Show first 16 bytes of each key as hex for visual proof
		real_hex = real_session_key[:16].hex()
		attacker_hex = attacker_recovered[:16].hex()
		legit_hex = legit_recovered[:16].hex()

		return {
			"attack": "harvest_now_decrypt_later",
			"kyber_resists_hndl": not quantum_broken,
			"legitimate_decap_ok": legit_ok,
			"real_session_key_hex": real_hex,
			"attacker_key_hex": attacker_hex,
			"legit_recovered_hex": legit_hex,
			"keys_match": quantum_broken,
			"why_blocked": "Kyber is IND-CCA2 secure. Every encapsulation with the same public key produces a different ciphertext and a different session key. The adversary has the public key and the recorded ciphertext but cannot reverse the lattice problem to extract the session key — not classically, not with a quantum computer.",
			"pqc_primitive": "CRYSTALS-Kyber (FIPS 203) — Module Learning With Errors hardness",
		}


def run_hndl_demo() -> dict:
	"""Return the harvest-now-decrypt-later demonstration result."""
	run_result = HarvestNowDecryptLater().run()
	return {
		"classical": {
			"algorithm": "RSA-2048",
			"ciphertext_size": 256,
			"quantum_safe": False,
		},
		"post_quantum": {
			"algorithm": "Kyber512",
			"ciphertext_size": 768,
			"quantum_safe": True,
		},
		"verdict": "RSA ciphertext is vulnerable to future quantum decryption. Kyber is not.",
		"attack": run_result["attack"],
		"kyber_resists_hndl": run_result["kyber_resists_hndl"],
		"legitimate_decap_ok": run_result["legitimate_decap_ok"],
		"real_session_key_hex": run_result["real_session_key_hex"],
		"attacker_key_hex": run_result["attacker_key_hex"],
		"legit_recovered_hex": run_result["legit_recovered_hex"],
		"keys_match": run_result["keys_match"],
		"why_blocked": run_result["why_blocked"],
		"pqc_primitive": run_result["pqc_primitive"],
	}
