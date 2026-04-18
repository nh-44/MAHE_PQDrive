"""Vehicle-side gateway that receives and validates OTA update requests."""

from __future__ import annotations

from datetime import datetime, timezone

from core.pipeline import OTAVerificationPipeline
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
		self._seen_request_ids: set[str] = set()
		self._pending_challenges: dict[str, str] = {}

	def issue_charger_challenge(self, request_id: str) -> str:
		"""Issue a nonce that a trusted charger must sign for this request."""
		from secrets import token_hex

		challenge = token_hex(16)
		self._pending_challenges[request_id] = challenge
		return challenge

	def receive_update_request(self, request: dict) -> dict:
		"""Validate OTA source and run cryptographic verification pipeline."""
		request_id = request.get("request_id")
		if request_id and request_id in self._seen_request_ids:
			return {
				"accepted": False,
				"failed_at": "replay",
				"reason": "request replay detected",
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

		if request_id:
			self._seen_request_ids.add(request_id)

		result = self.pipeline.run(request)
		result["accepted"] = result["all_passed"]
		if charger_auth and self.charger_security is not None:
			profile = self.charger_security._profiles.get(charger_auth.get("charger_id"))
			if profile is not None:
				result["charger_verified"] = True
				result["privacy_token"] = profile.pseudonymous_id
		return result
