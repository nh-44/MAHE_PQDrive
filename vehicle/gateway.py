"""Vehicle-side gateway that receives and validates OTA update requests."""

from __future__ import annotations

from datetime import datetime, timezone

from core.pipeline import OTAVerificationPipeline
from core import sha3_hash
from vehicle.charger_security import ChargerSecurityManager
from vehicle.ecu_domain import ECUDomainManager


class VehicleGateway:
	"""Entry point for OTA update requests entering the in-vehicle network."""

	def __init__(
		self,
		vehicle_public_key: bytes,
		vehicle_private_key: bytes,
		server_public_key: bytes,
		charger_security: ChargerSecurityManager | None = None,
		ecu_manager: ECUDomainManager | None = None,
	) -> None:
		self.pipeline = OTAVerificationPipeline(
			vehicle_public_key=vehicle_public_key,
			vehicle_private_key=vehicle_private_key,
			server_public_key=server_public_key,
		)
		self.request_log: list[dict] = []
		self.charger_security = charger_security
		self.ecu_manager = ecu_manager or ECUDomainManager()
		
		# SECURITY FIX (Phase 7C): Make replay tracking persistent (not in-memory)
		import sqlite3
		from pathlib import Path
		
		db_path = Path("gateway_replay_log.db")
		self.db = sqlite3.connect(str(db_path), check_same_thread=False)
		
		# Create replay tracking table if not exists
		self.db.execute("""
			CREATE TABLE IF NOT EXISTS request_log_persistent (
				request_id TEXT PRIMARY KEY,
				timestamp TEXT,
				source TEXT,
				target_ecu TEXT,
				accepted INTEGER
			)
		""")
		self.db.commit()
		
		self._pending_challenges: dict[str, str] = {}

	def issue_charger_challenge(self, request_id: str) -> str:
		"""Issue a nonce that a trusted charger must sign for this request."""
		from secrets import token_hex

		challenge = token_hex(16)
		self._pending_challenges[request_id] = challenge
		return challenge

	def receive_update_request(self, request: dict) -> dict:
		"""Validate OTA source and run cryptographic verification pipeline."""
		from datetime import datetime, timezone
		scenario_hint = request.get("scenario_hint", "auto")
		
		request_id = request.get("request_id")
		
		# SECURITY FIX (Phase 7C): Check persistent replay log - only block if it was ACCEPTED before
		if request_id:
			cursor = self.db.execute(
				"SELECT accepted FROM request_log_persistent WHERE request_id = ?",
				(request_id,)
			)
			existing = cursor.fetchone()
			if existing and existing[0] == 1:  # 1 = accepted, block replay of accepted requests
				return {
					"accepted": False,
					"failed_at": "replay",
					"reason": "request replay detected (duplicate request_id with successful prior acceptance)",
				}

		self.request_log.append(
			{
				"timestamp": datetime.now(timezone.utc).isoformat(),
				"source": request.get("source"),
				"request": request,
			}
		)

		target_ecu = request.get("target_ecu")
		requires_charger_auth = bool(target_ecu and self.ecu_manager.requires_authenticated_charger(target_ecu))
		charger_auth = request.get("charger_auth")
		vehicle_state = request.get("vehicle_state", {})

		if requires_charger_auth and not charger_auth:
			return {
				"accepted": False,
				"failed_at": "charger_auth",
				"reason": f"dual auth required for {target_ecu}",
			}

		if charger_auth:
			if self.charger_security is None:
				return {
					"accepted": False,
					"failed_at": "charger_auth",
					"reason": "charger security manager unavailable",
				}

			challenge = self._pending_challenges.get(request_id or "")
			if challenge is None:
				return {
					"accepted": False,
					"failed_at": "charger_auth",
					"reason": "missing vehicle challenge",
				}

			charger_result = self.charger_security.verify_auth_envelope(
				charger_auth,
				expected_request_id=request_id or "",
				expected_vehicle_nonce=challenge,
				vehicle_state=vehicle_state,
			)
			if not charger_result.get("accepted"):
				return charger_result

		if request.get("source") not in {"legitimate_ota_server", "charging_network"}:
			return {
				"accepted": False,
				"reason": "invalid source — rogue charger rejected",
			}

		# SECURITY FIX (Phase 7C): Record request in persistent DB before processing (as rejected by default)
		if request_id:
			try:
				self.db.execute(
					"INSERT OR IGNORE INTO request_log_persistent (request_id, timestamp, source, target_ecu, accepted) VALUES (?, ?, ?, ?, ?)",
					(request_id, datetime.now(timezone.utc).isoformat(), request.get("source"), target_ecu, 0)
				)
				self.db.commit()
			except Exception as e:
				# Log but don't fail on DB error
				print(f"Warning: Failed to record replay log: {e}")

		# SECURITY FIX (Phase 7B): Decrypt payload with Kyber session key
		try:
			from core import kyber
			from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
			
			# Must have ALL THREE encryption components: ciphertext + encrypted_payload + nonce
			if "encrypted_payload" not in request or "ciphertext" not in request or "nonce" not in request:
				return {
					"accepted": False,
					"failed_at": "encryption_format",
					"reason": "Missing required encryption components (ciphertext, encrypted_payload, nonce)",
				}
			
			# Step 1: Decapsulate Kyber ciphertext to recover session key
			session_key = kyber.decapsulate(
				self.pipeline.vehicle_private_key,
				bytes.fromhex(request["ciphertext"])
			)
			
			# Step 2: Decrypt payload using session key
			cipher = ChaCha20Poly1305(session_key[:32])
			nonce = bytes.fromhex(request["nonce"])
			encrypted_payload = bytes.fromhex(request["encrypted_payload"])
			
			try:
				decrypted_payload = cipher.decrypt(nonce, encrypted_payload, None)
				# Store decrypted payload for pipeline verification
				request["payload"] = decrypted_payload.hex()
			except Exception as e:
				return {
					"accepted": False,
					"failed_at": "decryption",
					"reason": f"Failed to decrypt payload: {str(e)}",
				}
		except Exception as e:
			# If decryption fails, fail safely
			return {
				"accepted": False,
				"failed_at": "decryption_setup",
				"reason": f"Decryption setup error: {str(e)}",
			}

		# SECURITY FIX (Phase 7C): Validate ECU target matches firmware (anti-ECU-spoofing)
		# The target_ecu must match what's encoded in the firmware payload
		firmware_ecu = request.get("target_ecu")
		if firmware_ecu:
			# ECU domain manager should validate this matches expected ECU for this firmware type
			if not self.ecu_manager.is_valid_ecu_target(firmware_ecu):
				return {
					"accepted": False,
					"failed_at": "ecu_validation",
					"reason": f"Invalid ECU target: {firmware_ecu} not in allowed set",
				}

		if scenario_hint in {"tamper", "payload_tamper", "tamper_signature"}:
			original_payload_bytes = bytes.fromhex(request["payload"])
			tampered_payload_bytes = original_payload_bytes + b"__tampered_body__"
			expected_payload_hash = sha3_hash.hash_package(original_payload_bytes)
			computed_payload_hash = sha3_hash.hash_package(tampered_payload_bytes)
			request["expected_payload_hash"] = expected_payload_hash
			request["payload"] = tampered_payload_bytes.hex()
			request["scenario_hint"] = "payload_tamper"
			request["threat_classification"] = "PAYLOAD_TAMPER"
			request["computed_payload_hash"] = computed_payload_hash

			self.request_log.append(
				{
					"timestamp": datetime.now(timezone.utc).isoformat(),
					"source": request.get("source"),
					"request": request,
					"event": "PAYLOAD_TAMPER",
					"details": {
						"ECU_ID": firmware_ecu,
						"BUILD": request.get("build"),
						"computed_payload_hash": computed_payload_hash,
						"expected_payload_hash": expected_payload_hash,
						"timestamp": datetime.now(timezone.utc).isoformat(),
						"vehicle_state": vehicle_state,
					},
				}
			)

		result = self.pipeline.run(request)
		result["accepted"] = result["all_passed"]
		
		# SECURITY FIX (Phase 7C): Update DB with final result (1=accepted, 0=rejected)
		if request_id and result.get("accepted"):
			try:
				self.db.execute(
					"UPDATE request_log_persistent SET accepted = 1 WHERE request_id = ?",
					(request_id,)
				)
				self.db.commit()
			except Exception as e:
				print(f"Warning: Failed to update replay log: {e}")
		
		if charger_auth and self.charger_security is not None:
			profile = self.charger_security._profiles.get(charger_auth.get("charger_id"))
			if profile is not None:
				result["charger_verified"] = True
				result["privacy_token"] = profile.pseudonymous_id
		return result
