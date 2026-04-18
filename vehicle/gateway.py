"""Vehicle-side gateway that receives and validates OTA update requests."""

from __future__ import annotations

from datetime import datetime, timezone

from core.pipeline import OTAVerificationPipeline


class VehicleGateway:
	"""Entry point for OTA update requests entering the in-vehicle network."""

	def __init__(
		self,
		vehicle_public_key: bytes,
		vehicle_private_key: bytes,
		server_public_key: bytes,
	) -> None:
		self.pipeline = OTAVerificationPipeline(
			vehicle_public_key=vehicle_public_key,
			vehicle_private_key=vehicle_private_key,
			server_public_key=server_public_key,
		)
		self.request_log: list[dict] = []

	def receive_update_request(self, request: dict) -> dict:
		"""Validate OTA source and run cryptographic verification pipeline."""
		self.request_log.append(
			{
				"timestamp": datetime.now(timezone.utc).isoformat(),
				"source": request.get("source"),
				"request": request,
			}
		)

		if request.get("source") != "legitimate_ota_server":
			return {
				"accepted": False,
				"reason": "invalid source — rogue charger rejected",
			}

		result = self.pipeline.run(request)
		return {"accepted": result["all_passed"], **result}
