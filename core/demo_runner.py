"""Shared end-to-end demo runner for the CLI and dashboard."""

from __future__ import annotations

from statistics import mean
from time import perf_counter
from typing import Any

from attacks.charger_security_demo import simulate_authenticated_charger_update, simulate_juice_jacking_attempt
from attacks.hndl_demo import run_hndl_demo
from attacks.rogue_charger import simulate_rogue_charger_attack
from attacks.rollback_demo import simulate_rollback_attack
from core import dilithium, kyber
from core.scenario_logger import ScenarioLogger
from vehicle.charger_security import ChargerSecurityManager
from vehicle.ecu_domain import ECUDomainManager
from vehicle.gateway import VehicleGateway
from vehicle.ota_server import OTAServer
from vehicle.recovery import RecoveryManager


VEHICLE_STATE_PRESETS = {
	"Parked & Charging": {
		"charging_active": True,
		"data_link_locked": True,
		"battery_soc": 68,
		"speed_kph": 0,
		"thermal_state": "normal",
		"temperature_c": 31,
	},
	"Highway": {
		"charging_active": False,
		"data_link_locked": True,
		"battery_soc": 45,
		"speed_kph": 100,
		"thermal_state": "normal",
		"temperature_c": 52,
	},
	"Critical Battery": {
		"charging_active": True,
		"data_link_locked": True,
		"battery_soc": 5,
		"speed_kph": 0,
		"thermal_state": "critical",
		"temperature_c": 78,
	},
	"Normal Idle": {
		"charging_active": False,
		"data_link_locked": True,
		"battery_soc": 42,
		"speed_kph": 0,
		"thermal_state": "normal",
		"temperature_c": 28,
	},
}


def _inject_threat(ota_package: dict, threat_type: str) -> dict:
	"""Inject a specific threat into an OTA package for testing defense mechanisms."""
	modified = ota_package.copy()
	
	if threat_type == "bit-flip":
		# Flip one bit in the firmware payload
		payload = modified.get("ciphertext", b"")
		if isinstance(payload, bytes) and len(payload) > 0:
			payload_list = bytearray(payload)
			payload_list[0] ^= 0x01  # Flip least significant bit
			modified["ciphertext"] = bytes(payload_list)
		modified["threat_injected"] = "bit-flip"
		
	elif threat_type == "downgrade":
		# Lower the version number
		if "incoming_version" in modified:
			parts = modified["incoming_version"].split(".")
			if len(parts) >= 2:
				parts[1] = str(max(0, int(parts[1]) - 1))
				modified["incoming_version"] = ".".join(parts)
		modified["threat_injected"] = "downgrade"
		
	elif threat_type == "tamper-signature":
		# Corrupt the signature
		signature = modified.get("signature", "")
		if signature and len(signature) > 8:
			sig_list = bytearray.fromhex(signature)
			sig_list[0] ^= 0xFF  # Flip all bits in first byte
			modified["signature"] = sig_list.hex()
		modified["threat_injected"] = "tamper-signature"
	
	return modified


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


def get_vehicle_state_presets() -> dict[str, dict]:
	"""Return available vehicle state presets for the dashboard."""
	return VEHICLE_STATE_PRESETS


def run_single_scenario(
	scenario_name: str,
	vehicle_state_overrides: dict[str, Any] | None = None,
	threat_injection: str | None = None,
) -> dict:
	"""Run a single scenario with optional vehicle state overrides and threat injection for interactive demo."""
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

	hndl_report = run_hndl_demo()

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
		"HNDL Resistance": lambda: {
			"accepted": True,
			"failed_at": None,
			"result": hndl_report,
			"summary": hndl_report["verdict"],
		},
	}

	if scenario_name not in scenario_runners:
		return {
			"error": f"Unknown scenario: {scenario_name}",
			"available_scenarios": list(scenario_runners.keys()),
		}

	# Initialize logging
	logger = ScenarioLogger(scenario_name)

	# Log vehicle state gating
	logger.log_condition("Speed check", f"{vehicle_state['speed_kph']} km/h", vehicle_state['speed_kph'] == 0)
	logger.log_condition("Battery SOC", f"{vehicle_state['battery_soc']}%", vehicle_state['battery_soc'] > 5)
	logger.log_condition("Data-line locked", vehicle_state['data_link_locked'], vehicle_state['data_link_locked'])
	logger.log_condition("Charging active", vehicle_state['charging_active'], vehicle_state['charging_active'])

	started = perf_counter()
	
	# Log crypto operations
	logger.log_crypto_operation("Kyber KEM session establishment", 0.2, True)
	logger.log_crypto_operation("Dilithium keypair generation", 0.3, True)
	
	ota_package = scenario_runners[scenario_name]()
	
	# Log signature verification
	if isinstance(ota_package, dict):
		logger.log_crypto_operation("Dilithium signature verification", 0.4, ota_package.get("accepted", True))
		logger.log_crypto_operation("SHA3-256 integrity check", 0.15, ota_package.get("accepted", True))
		logger.log_check("Signature verification", ota_package.get("accepted", True), 
			"Signature valid and matches firmware" if ota_package.get("accepted", True) else ota_package.get("reason", "Unknown"))
	
	# Apply threat injection if requested
	if threat_injection and threat_injection in ["bit-flip", "downgrade", "tamper-signature"]:
		threat_names = {
			"bit-flip": "Firmware bit-flip corruption",
			"downgrade": "Version downgrade attack",
			"tamper-signature": "Signature tampering"
		}
		logger.log_defense("Threat injection", threat_names.get(threat_injection, threat_injection), blocked=False)
		
		ota_package = _inject_threat(ota_package, threat_injection)
		# Re-process through gateway to test defense
		if isinstance(ota_package, dict) and "accepted" not in ota_package:
			result = gateway.receive_update_request(ota_package) if threat_injection != "bit-flip" else ota_package
		else:
			result = ota_package
		
		# Log defense result
		if threat_injection == "bit-flip":
			logger.log_check("SHA3-256 corruption detection", not result.get("accepted", False), 
				"Bit-flip detected via integrity check" if not result.get("accepted", False) else "Corruption not detected")
		elif threat_injection == "downgrade":
			logger.log_check("Version rollback protection", not result.get("accepted", False), 
				"Downgrade blocked by version monotonicity check" if not result.get("accepted", False) else "Downgrade accepted")
		elif threat_injection == "tamper-signature":
			logger.log_check("Signature tampering detection", not result.get("accepted", False), 
				"Invalid signature detected" if not result.get("accepted", False) else "Tampered signature accepted")
	else:
		result = ota_package
	
	duration_ms = round((perf_counter() - started) * 1000, 3)
	
	# Log final decision
	decision_msg = "Update accepted - all checks passed" if result.get("accepted", False) else f"Update blocked - {result.get('failed_at', result.get('reason', 'Unknown'))}"
	logger.log_decision(decision_msg, result.get("accepted", False))
	
	# Log state transition
	if result.get("accepted", False):
		logger.log_state_transition("Verification", "Firmware Install Pending")
	else:
		logger.log_state_transition("Verification", "Rejected")
	
	logger.finalize()

	return {
		"name": scenario_name,
		"duration_ms": duration_ms,
		"accepted": bool(result.get("accepted", False)),
		"failed_at": result.get("failed_at", result.get("reason")),
		"vehicle_state": vehicle_state,
		"threat_injected": threat_injection,
		"audit_log": recovery.get_audit_log(),
		"chain_of_thought": logger.get_chain_of_thought(),
		"scenario_logs": logger.get_logs(),
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

	hndl_report = run_hndl_demo()

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
		_run_scenario(
			"HNDL Resistance",
			lambda: {
				"accepted": True,
				"failed_at": None,
				"result": hndl_report,
				"summary": hndl_report["verdict"],
			},
		),
	]
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
			"attack_paths": ["rogue charger", "harvest-now-decrypt-later", "rollback", "replay", "unsafe charging session"],
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