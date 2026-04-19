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

	# Convert hex payload back to bytes for tampering
	payload_bytes = bytes.fromhex(package["payload"])
	tampered = bytearray(payload_bytes)
	tampered[0] ^= 0x01
	package["payload"] = tampered.hex()  # Store back as hex

	return gateway.receive_update_request(package)
