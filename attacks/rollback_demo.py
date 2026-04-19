"""Rollback attack simulation for OTA version control enforcement."""

from __future__ import annotations

from vehicle.gateway import VehicleGateway
from vehicle.ota_server import OTAServer


def simulate_rollback_attack(gateway: VehicleGateway, server: OTAServer) -> dict:
	"""Prepare downgrade package and return gateway verification outcome."""
	package = server.prepare_update(
		payload=b"firmware_old_payload",
		current_version="2.0.0",
		new_version="1.0.0",
	)
	return gateway.receive_update_request(package)
