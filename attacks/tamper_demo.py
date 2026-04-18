"""Payload tampering attack simulation to test integrity validation."""

from __future__ import annotations

from vehicle.gateway import VehicleGateway
from vehicle.ota_server import OTAServer


def simulate_tamper_attack(gateway: VehicleGateway, server: OTAServer) -> dict:
	"""Mutate payload bytes after package preparation and send to gateway."""
	package = server.prepare_update(
		payload=b"firmware_v2_legit",
		current_version="1.0.0",
		new_version="2.0.0",
	)

	tampered = bytearray(package["payload"])
	tampered[0] ^= 0x01
	package["payload"] = bytes(tampered)

	return gateway.receive_update_request(package)
