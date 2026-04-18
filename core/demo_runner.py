"""Shared end-to-end demo runner for the CLI and dashboard."""

from __future__ import annotations

from statistics import mean
from time import perf_counter
from typing import Any

from attacks.charger_security_demo import simulate_authenticated_charger_update, simulate_juice_jacking_attempt
from attacks.hndl_demo import run_hndl_demo
from attacks.rogue_charger import simulate_rogue_charger_attack
from attacks.rollback_demo import simulate_rollback_attack
from attacks.tamper_demo import simulate_tamper_attack
from core import dilithium, kyber
from vehicle.charger_security import ChargerSecurityManager
from vehicle.ecu_domain import ECUDomainManager
from vehicle.gateway import VehicleGateway
from vehicle.ota_server import OTAServer
from vehicle.recovery import RecoveryManager


def _run_scenario(name: str, runner) -> dict:
	started = perf_counter()
	result = runner()
	duration_ms = round((perf_counter() - started) * 1000, 3)
	return {
		"name": name,
		"duration_ms": duration_ms,
		"accepted": bool(result.get("accepted", False)),
		"failed_at": result.get("failed_at", result.get("reason")),
		"result": result,
	}


def run_single_scenario(scenario_name: str, vehicle_state_overrides: dict[str, Any] | None = None) -> dict:
	"""Run a single scenario with optional vehicle state overrides for interactive demo."""
	if vehicle_state_overrides is None:
		vehicle_state_overrides = {}

	vehicle_public_key, vehicle_private_key = kyber.generate_keypair()
	server_public_key, server_private_key = dilithium.generate_keypair()
	ecu_manager = ECUDomainManager()
	charger_manager = ChargerSecurityManager()
	trusted_charger = charger_manager.register_charger("north-road-fast-charger")
	recovery = RecoveryManager()

	server = OTAServer(
		server_private_key=server_private_key,
		server_public_key=server_public_key,
		vehicle_public_key=vehicle_public_key,
	)
	gateway = VehicleGateway(
		vehicle_public_key=vehicle_public_key,
		vehicle_private_key=vehicle_private_key,
		server_public_key=server_public_key,
		charger_security=charger_manager,
		ecu_manager=ecu_manager,
	)

	# Default vehicle state
	default_state = {
		"charging_active": True,
		"data_link_locked": True,
		"battery_soc": 68,
		"speed_kph": 0,
		"thermal_state": "normal",
		"temperature_c": 31,
	}
	default_state.update(vehicle_state_overrides)
	vehicle_state = default_state

	recovery.take_snapshot(
		"braking_ecu",
		"2.0.0",
		vehicle_state,
	)

	# Scenario runners
	scenario_runners: dict[str, callable] = {
		"Legitimate OTA": lambda: gateway.receive_update_request(
			server.prepare_update(
				payload=b"firmware_v2",
				current_version="1.0.0",
				new_version="2.0.0",
				target_ecu="maps_ecu",
			)
		),
		"Trusted Charger OTA": lambda: simulate_authenticated_charger_update(
			gateway,
			server,
			charger_manager,
			trusted_charger,
			target_ecu="braking_ecu",
		),
		"Anti-Juice Jacking": lambda: simulate_juice_jacking_attempt(
			gateway,
			server,
			charger_manager,
			trusted_charger,
			target_ecu="braking_ecu",
		),
		"Replay Attack": lambda: gateway.receive_update_request(
			server.prepare_update(
				payload=b"firmware_v3_secure",
				current_version="2.0.0",
				new_version="2.1.0",
				target_ecu="braking_ecu",
			)
		) or gateway.receive_update_request(
			server.prepare_update(
				payload=b"firmware_v3_secure",
				current_version="2.0.0",
				new_version="2.1.0",
				target_ecu="braking_ecu",
			)
		),
		"Rogue Charger Attack": lambda: simulate_rogue_charger_attack(gateway),
		"Rollback Attack": lambda: simulate_rollback_attack(gateway, server),
		"Tamper Attack": lambda: simulate_tamper_attack(gateway, server),
	}

	if scenario_name not in scenario_runners:
		return {
			"error": f"Unknown scenario: {scenario_name}",
			"available_scenarios": list(scenario_runners.keys()),
		}

	started = perf_counter()
	result = scenario_runners[scenario_name]()
	duration_ms = round((perf_counter() - started) * 1000, 3)

	return {
		"name": scenario_name,
		"duration_ms": duration_ms,
		"accepted": bool(result.get("accepted", False)),
		"failed_at": result.get("failed_at", result.get("reason")),
		"vehicle_state": vehicle_state,
		"result": result,
	}


def build_demo_report() -> dict:
	"""Run the project demo flow and return structured output for UI/CLI use."""
	vehicle_public_key, vehicle_private_key = kyber.generate_keypair()
	server_public_key, server_private_key = dilithium.generate_keypair()
	ecu_manager = ECUDomainManager()
	charger_manager = ChargerSecurityManager()
	trusted_charger = charger_manager.register_charger("north-road-fast-charger")
	recovery = RecoveryManager()

	server = OTAServer(
		server_private_key=server_private_key,
		server_public_key=server_public_key,
		vehicle_public_key=vehicle_public_key,
	)
	gateway = VehicleGateway(
		vehicle_public_key=vehicle_public_key,
		vehicle_private_key=vehicle_private_key,
		server_public_key=server_public_key,
		charger_security=charger_manager,
		ecu_manager=ecu_manager,
	)

	recovery.take_snapshot(
		"braking_ecu",
		"2.0.0",
		{"mode": "steady", "battery_soc": 64, "temperature_c": 31},
	)

	def legitimate_ota() -> dict:
		package = server.prepare_update(
			payload=b"firmware_v2",
			current_version="1.0.0",
			new_version="2.0.0",
			target_ecu="maps_ecu",
		)
		return gateway.receive_update_request(package)

	def secure_charger_update() -> dict:
		return simulate_authenticated_charger_update(
			gateway,
			server,
			charger_manager,
			trusted_charger,
			target_ecu="braking_ecu",
		)

	def replay_attack() -> dict:
		package = server.prepare_update(
			payload=b"firmware_v3_secure",
			current_version="2.0.0",
			new_version="2.1.0",
			target_ecu="braking_ecu",
		)
		vehicle_state = {
			"charging_active": True,
			"data_link_locked": True,
			"battery_soc": 68,
			"speed_kph": 0,
			"thermal_state": "normal",
			"temperature_c": 31,
		}
		vehicle_nonce = gateway.issue_charger_challenge(package["request_id"])
		charger_auth = charger_manager.build_auth_envelope(
			trusted_charger.charger_id,
			package["request_id"],
			vehicle_nonce,
			vehicle_state,
		)
		package.update({"source": "charging_network", "charger_auth": charger_auth, "vehicle_state": vehicle_state})
		gateway.receive_update_request(package)
		return gateway.receive_update_request(package)

	scenarios = [
		_run_scenario("Legitimate OTA", legitimate_ota),
		_run_scenario("Trusted Charger OTA", secure_charger_update),
		_run_scenario("Anti-Juice Jacking", lambda: simulate_juice_jacking_attempt(gateway, server, charger_manager, trusted_charger, target_ecu="braking_ecu")),
		_run_scenario("Replay Attack", replay_attack),
		_run_scenario("Rogue Charger Attack", lambda: simulate_rogue_charger_attack(gateway)),
		_run_scenario("Rollback Attack", lambda: simulate_rollback_attack(gateway, server)),
		_run_scenario("Tamper Attack", lambda: simulate_tamper_attack(gateway, server)),
	]

	hndl_report = run_hndl_demo()
	stage_timings: list[float] = []
	for scenario in scenarios:
		stage_timings.extend(scenario["result"].get("stage_durations_ms", {}).values())
	metrics = {
		"scenario_count": len(scenarios),
		"accepted_count": sum(1 for scenario in scenarios if scenario["accepted"]),
		"blocked_count": sum(1 for scenario in scenarios if not scenario["accepted"]),
		"mean_latency_ms": round(mean(scenario["duration_ms"] for scenario in scenarios), 3),
		"fastest_stage_ms": round(min(stage_timings), 3) if stage_timings else 0.0,
	}

	return {
		"title": "PQDrive OTA and Charger Security Demo",
		"threat_model": {
			"entry_points": ["OTA request ingress", "charger-authenticated update path", "CAN simulation bus"],
			"attack_paths": ["rogue charger", "payload tamper", "rollback", "replay", "unsafe charging session"],
			"target_systems": ["gateway", "vehicle OTA pipeline", "safety-critical ECU policy", "recovery manager"],
		},
		"policy": {
			"dual_auth_required_for": ["braking_ecu", "steering_ecu", "adas_ecu", "powertrain_ecu"],
			"trusted_charger": trusted_charger.pseudonymous_id,
		},
		"scenarios": scenarios,
		"hndl": hndl_report,
		"recovery": recovery.get_audit_log(),
		"metrics": metrics,
		"recommendations": [
			"Move charger attestations to real certificates and mTLS for production deployment.",
			"Persist request IDs and nonces in durable storage for reboot-safe replay defense.",
			"Expose per-stage verification timing and policy decisions in the dashboard.",
			"Add a signed artifact manifest for the OTA payload and metadata.",
		],
	}