"""Charged-network attack and defense simulations for the hackathon demo."""

from __future__ import annotations

from typing import Any

from vehicle.charger_security import ChargerSecurityManager
from vehicle.gateway import VehicleGateway
from vehicle.ota_server import OTAServer


def _build_secure_request(
	gateway: VehicleGateway,
	server: OTAServer,
	charger_manager: ChargerSecurityManager,
	charger_profile,
	target_ecu: str,
	vehicle_state: dict[str, Any],
) -> dict:
	package = server.prepare_update(
		payload=b"firmware_v3_secure",
		current_version="2.0.0",
		new_version="2.1.0",
		target_ecu=target_ecu,
	)
	vehicle_nonce = gateway.issue_charger_challenge(package["request_id"])
	charger_auth = charger_manager.build_auth_envelope(
		charger_profile.charger_id,
		package["request_id"],
		vehicle_nonce,
		vehicle_state,
	)
	package.update(
		{
			"source": "charging_network",
			"charger_auth": charger_auth,
			"vehicle_state": vehicle_state,
		}
	)
	return package


def simulate_authenticated_charger_update(
	gateway: VehicleGateway,
	server: OTAServer,
	charger_manager: ChargerSecurityManager,
	charger_profile,
	target_ecu: str = "braking_ecu",
) -> dict:
	"""Show a trusted charger forwarding a valid update to a safety-critical ECU."""
	safe_state = {
		"charging_active": True,
		"data_link_locked": True,
		"battery_soc": 68,
		"speed_kph": 0,
		"thermal_state": "normal",
		"temperature_c": 31,
	}
	request = _build_secure_request(gateway, server, charger_manager, charger_profile, target_ecu, safe_state)
	return gateway.receive_update_request(request)


def simulate_juice_jacking_attempt(
	gateway: VehicleGateway,
	server: OTAServer,
	charger_manager: ChargerSecurityManager,
	charger_profile,
	target_ecu: str = "braking_ecu",
) -> dict:
	"""Show an unsafe charger session being rejected before OTA verification."""
	unsafe_state = {
		"charging_active": True,
		"data_link_locked": False,
		"battery_soc": 57,
		"speed_kph": 0,
		"thermal_state": "normal",
		"temperature_c": 29,
	}
	request = _build_secure_request(gateway, server, charger_manager, charger_profile, target_ecu, unsafe_state)
	return gateway.receive_update_request(request)