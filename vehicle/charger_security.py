"""Charger authentication and anti-juice protections for vehicle-side OTA."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import secrets
from typing import Any

from core import dilithium, sha3_hash


MAX_SAFE_SPEED_KPH = 0
MIN_BATTERY_SOC = 20
MAX_SAFE_TEMPERATURE_C = 60
MAX_CLOCK_SKEW_SECONDS = 300


def _canonical_json(payload: dict) -> bytes:
	return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


@dataclass
class ChargerProfile:
	charger_id: str
	charger_name: str
	pseudonymous_id: str
	public_key: bytes
	private_key: bytes
	capabilities: list[str] = field(default_factory=list)


class ChargerSecurityManager:
	"""Track trusted chargers and verify charger-authenticated OTA requests."""

	def __init__(self) -> None:
		self._profiles: dict[str, ChargerProfile] = {}
		self._seen_request_ids: set[str] = set()

	def register_charger(self, charger_name: str, capabilities: list[str] | None = None) -> ChargerProfile:
		"""Create a trusted charger profile with a pseudonymous identifier."""
		public_key, private_key = dilithium.generate_keypair()
		charger_id = secrets.token_hex(8)
		pseudonymous_id = sha3_hash.hash_package(f"{charger_name}:{charger_id}".encode("utf-8"))[:24]
		profile = ChargerProfile(
			charger_id=charger_id,
			charger_name=charger_name,
			pseudonymous_id=pseudonymous_id,
			public_key=public_key,
			private_key=private_key,
			capabilities=capabilities or ["ota_forwarding", "vehicle_auth"],
		)
		self._profiles[charger_id] = profile
		return profile

	def issue_vehicle_nonce(self) -> str:
		"""Create a fresh nonce for a charger-to-vehicle authentication round."""
		return secrets.token_hex(16)

	def build_auth_envelope(
		self,
		charger_id: str,
		request_id: str,
		vehicle_nonce: str,
		vehicle_state: dict[str, Any],
		intent: str = "ota",
	) -> dict:
		"""Build a signed charger attestation envelope for a specific OTA request."""
		profile = self._profiles[charger_id]
		state_digest = hashlib.sha3_256(_canonical_json(vehicle_state)).hexdigest()
		envelope = {
			"charger_id": charger_id,
			"pseudonymous_id": profile.pseudonymous_id,
			"charger_name": profile.charger_name,
			"request_id": request_id,
			"vehicle_nonce": vehicle_nonce,
			"intent": intent,
			"vehicle_state_digest": state_digest,
			"timestamp": datetime.now(timezone.utc).isoformat(),
		}
		signature = dilithium.sign(profile.private_key, _canonical_json(envelope))
		envelope["signature"] = signature.hex()
		return envelope

	def verify_auth_envelope(
		self,
		envelope: dict,
		expected_request_id: str,
		expected_vehicle_nonce: str,
		vehicle_state: dict[str, Any],
	) -> dict:
		"""Verify a charger attestation and reject replay or unsafe charging states."""
		charger_id = envelope.get("charger_id")
		profile = self._profiles.get(charger_id)
		if profile is None:
			return {"accepted": False, "failed_at": "charger_identity", "reason": "untrusted charger"}

		if envelope.get("request_id") != expected_request_id:
			return {"accepted": False, "failed_at": "charger_replay", "reason": "request mismatch"}

		if expected_request_id in self._seen_request_ids:
			return {"accepted": False, "failed_at": "charger_replay", "reason": "replayed charger attestation"}

		if envelope.get("vehicle_nonce") != expected_vehicle_nonce:
			return {"accepted": False, "failed_at": "charger_nonce", "reason": "nonce mismatch"}

		try:
			envelope_time = datetime.fromisoformat(envelope.get("timestamp"))
		except (TypeError, ValueError):
			return {"accepted": False, "failed_at": "charger_timestamp", "reason": "invalid charger timestamp"}

		age_seconds = abs((datetime.now(timezone.utc) - envelope_time).total_seconds())
		if age_seconds > MAX_CLOCK_SKEW_SECONDS:
			return {"accepted": False, "failed_at": "charger_timestamp", "reason": "stale charger attestation"}

		state_digest = hashlib.sha3_256(_canonical_json(vehicle_state)).hexdigest()
		if envelope.get("vehicle_state_digest") != state_digest:
			return {"accepted": False, "failed_at": "charger_state", "reason": "vehicle state mismatch"}

		if not self._is_safe_charging_state(vehicle_state):
			return {"accepted": False, "failed_at": "anti_juice", "reason": "unsafe charging condition"}

		try:
			signature = bytes.fromhex(envelope.get("signature", ""))
		except ValueError:
			return {"accepted": False, "failed_at": "charger_signature", "reason": "invalid signature encoding"}

		signed_payload = {
			key: envelope[key]
			for key in ("charger_id", "pseudonymous_id", "charger_name", "request_id", "vehicle_nonce", "intent", "vehicle_state_digest", "timestamp")
		}
		if not dilithium.verify(profile.public_key, _canonical_json(signed_payload), signature):
			return {"accepted": False, "failed_at": "charger_signature", "reason": "charger signature invalid"}

		self._seen_request_ids.add(expected_request_id)
		return {
			"accepted": True,
			"failed_at": None,
			"reason": "charger attestation accepted",
			"privacy_token": profile.pseudonymous_id,
			"charger_capabilities": profile.capabilities,
		}

	def _is_safe_charging_state(self, vehicle_state: dict[str, Any]) -> bool:
		"""Reject states that make charger-mediated OTA unsafe."""
		if not vehicle_state:
			return True

		if vehicle_state.get("charging_active") and not vehicle_state.get("data_link_locked", False):
			return False

		if float(vehicle_state.get("speed_kph", 0)) > MAX_SAFE_SPEED_KPH:
			return False

		battery_soc = float(vehicle_state.get("battery_soc", 100))
		if vehicle_state.get("charging_active") and battery_soc < MIN_BATTERY_SOC:
			return False

		thermal_state = str(vehicle_state.get("thermal_state", "normal")).lower()
		if thermal_state in {"hot", "critical", "overheat"}:
			return False

		if float(vehicle_state.get("temperature_c", 25)) > MAX_SAFE_TEMPERATURE_C:
			return False

		return True