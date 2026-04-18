"""Rogue charger attack simulation against vehicle gateway source validation."""

from __future__ import annotations

from vehicle.gateway import VehicleGateway


def simulate_rogue_charger_attack(gateway: VehicleGateway) -> dict:
	"""Send a fake package from an untrusted source and return gateway response."""
	fake_request = {
		"source": "rogue_charger",
		"payload": b"malicious_firmware",
		"incoming_version": "9.9.9",
		"current_version": "1.0.0",
	}
	return gateway.receive_update_request(fake_request)
