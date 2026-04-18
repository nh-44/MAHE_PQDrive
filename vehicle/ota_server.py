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
		"""Prepare a full OTA package for vehicle gateway validation."""
		ciphertext, session_key = kyber.encapsulate(self.vehicle_public_key)
		signature = dilithium.sign(self.server_private_key, payload)
		package_hash = sha3_hash.hash_package(payload)
		issued_at = datetime.now(timezone.utc)
		request_id = uuid4().hex

		return {
			"ciphertext": ciphertext,
			"session_key": session_key,
			"signature": signature,
			"payload": payload,
			"package_hash": package_hash,
			"incoming_version": new_version,
			"current_version": current_version,
			"target_ecu": target_ecu,
			"request_id": request_id,
			"issued_at": issued_at.isoformat(),
			"expires_at": (issued_at + timedelta(minutes=10)).isoformat(),
			"source": "legitimate_ota_server",
		}
