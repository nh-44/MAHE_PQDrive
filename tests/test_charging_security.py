from __future__ import annotations

from core import dilithium, kyber
from vehicle.charger_security import ChargerSecurityManager
from vehicle.ecu_domain import ECUDomainManager
from vehicle.gateway import VehicleGateway
from vehicle.ota_server import OTAServer


def _build_gateway() -> tuple[VehicleGateway, OTAServer, ChargerSecurityManager, object]:
	vehicle_public_key, vehicle_private_key = kyber.generate_keypair()
	server_public_key, server_private_key = dilithium.generate_keypair()
	charger_manager = ChargerSecurityManager()
	charger_profile = charger_manager.register_charger("test-charger")
	gateway = VehicleGateway(
		vehicle_public_key=vehicle_public_key,
		vehicle_private_key=vehicle_private_key,
		server_public_key=server_public_key,
		charger_security=charger_manager,
		ecu_manager=ECUDomainManager(),
	)
	server = OTAServer(
		server_private_key=server_private_key,
		server_public_key=server_public_key,
		vehicle_public_key=vehicle_public_key,
	)
	return gateway, server, charger_manager, charger_profile


def test_authenticated_charger_update_passes() -> None:
	gateway, server, charger_manager, charger_profile = _build_gateway()
	package = server.prepare_update(
		payload=b"firmware_v3_secure",
		current_version="2.0.0",
		new_version="2.1.0",
		target_ecu="braking_ecu",
	)
	vehicle_state = {
		"charging_active": True,
		"data_link_locked": True,
		"battery_soc": 62,
		"speed_kph": 0,
		"thermal_state": "normal",
		"temperature_c": 31,
	}
	vehicle_nonce = gateway.issue_charger_challenge(package["request_id"])
	charger_auth = charger_manager.build_auth_envelope(
		charger_profile.charger_id,
		package["request_id"],
		vehicle_nonce,
		vehicle_state,
	)
	package.update({"source": "charging_network", "charger_auth": charger_auth, "vehicle_state": vehicle_state})

	result = gateway.receive_update_request(package)

	assert result["accepted"] is True
	assert result["charger_verified"] is True
	assert result["all_passed"] is True


def test_anti_juice_jacking_blocked() -> None:
	gateway, server, charger_manager, charger_profile = _build_gateway()
	package = server.prepare_update(
		payload=b"firmware_v3_secure",
		current_version="2.0.0",
		new_version="2.1.0",
		target_ecu="braking_ecu",
	)
	vehicle_state = {
		"charging_active": True,
		"data_link_locked": False,
		"battery_soc": 62,
		"speed_kph": 0,
		"thermal_state": "normal",
		"temperature_c": 31,
	}
	vehicle_nonce = gateway.issue_charger_challenge(package["request_id"])
	charger_auth = charger_manager.build_auth_envelope(
		charger_profile.charger_id,
		package["request_id"],
		vehicle_nonce,
		vehicle_state,
	)
	package.update({"source": "charging_network", "charger_auth": charger_auth, "vehicle_state": vehicle_state})

	result = gateway.receive_update_request(package)

	assert result["accepted"] is False
	assert result["failed_at"] == "anti_juice"


def test_replayed_charger_request_blocked() -> None:
	gateway, server, charger_manager, charger_profile = _build_gateway()
	package = server.prepare_update(
		payload=b"firmware_v3_secure",
		current_version="2.0.0",
		new_version="2.1.0",
		target_ecu="braking_ecu",
	)
	vehicle_state = {
		"charging_active": True,
		"data_link_locked": True,
		"battery_soc": 62,
		"speed_kph": 0,
		"thermal_state": "normal",
		"temperature_c": 31,
	}
	vehicle_nonce = gateway.issue_charger_challenge(package["request_id"])
	charger_auth = charger_manager.build_auth_envelope(
		charger_profile.charger_id,
		package["request_id"],
		vehicle_nonce,
		vehicle_state,
	)
	package.update({"source": "charging_network", "charger_auth": charger_auth, "vehicle_state": vehicle_state})

	first_result = gateway.receive_update_request(package)
	second_result = gateway.receive_update_request(package)

	assert first_result["accepted"] is True
	assert second_result["accepted"] is False
	assert second_result["failed_at"] == "replay"