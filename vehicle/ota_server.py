"""Server-side OTA package preparation using post-quantum primitives."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from core import dilithium, kyber, sha3_hash


class OTAServer:
	"""Constructs signed and encapsulated OTA update packages."""

	def __init__(
		self,
		server_private_key: bytes,
		server_public_key: bytes,
		vehicle_public_key: bytes,
	) -> None:
		self.server_private_key = server_private_key
		self.server_public_key = server_public_key
		self.vehicle_public_key = vehicle_public_key

	def prepare_update(
		self,
		payload: bytes,
		current_version: str,
		new_version: str,
		target_ecu: str = "maps_ecu",
	) -> dict:
		"""Prepare a full OTA package for vehicle gateway validation.
		
		SECURITY FIX (Phase 7B): Encrypt payload with Kyber session key using ChaCha20Poly1305.
		"""
		import os
		from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
		
		# Stage 1: Kyber KEM - generate encapsulated secret
		ciphertext, session_key = kyber.encapsulate(self.vehicle_public_key)
		
		# SECURITY FIX: Encrypt payload with session key (not plaintext)
		cipher = ChaCha20Poly1305(session_key[:32])  # Use first 32 bytes for 256-bit key
		nonce = os.urandom(12)  # IV for ChaCha20Poly1305
		encrypted_payload = cipher.encrypt(nonce, payload, None)
		
		# Stage 2: Sign PLAINTEXT payload (signature proves origin before encryption)
		signature = dilithium.sign(self.server_private_key, payload)
		
		# Stage 3: Hash package
		package_hash = sha3_hash.hash_package(payload)
		
		# Metadata
		issued_at = datetime.now(timezone.utc)
		request_id = uuid4().hex

		return {
			"ciphertext": ciphertext.hex(),            # Convert bytes to hex
			# "session_key": session_key,  # SECURITY FIX: Don't send key! Only encapsulated secret.
			"encrypted_payload": encrypted_payload.hex(),  # SECURITY FIX: Hex-encode for JSON
			"nonce": nonce.hex(),                     # SECURITY FIX: Send nonce for decryption
			"signature": signature.hex(),
			"payload": payload.hex(),  # Include for testing/demo (gateway ignores, uses decrypted version)
			"package_hash": package_hash,              # Already hex string from hash_package()
			"incoming_version": new_version,
			"current_version": current_version,
			"target_ecu": target_ecu,
			"request_id": request_id,
			"issued_at": issued_at.isoformat(),
			"expires_at": (issued_at + timedelta(minutes=10)).isoformat(),
			"source": "legitimate_ota_server",
		}
