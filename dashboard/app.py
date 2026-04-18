"""Flask dashboard for the OTA and charger security demo."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from functools import wraps
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

from core.demo_runner import build_demo_report, run_single_scenario, get_vehicle_state_presets
from core.payload_classifier import classify_payload, evaluate_delivery_gate, parse_firmware_payload
from vehicle.recovery import RecoveryManager


# SECURITY FIX (Phase 7C): DOS protection via rate limiting
class RateLimiter:
	"""Simple in-memory rate limiter for DOS protection."""
	
	def __init__(self, max_requests: int = 100, window_seconds: int = 60):
		"""Initialize rate limiter.
		
		Args:
			max_requests: Maximum requests per window
			window_seconds: Time window in seconds
		"""
		self.max_requests = max_requests
		self.window_seconds = window_seconds
		self.requests = defaultdict(list)  # IP -> [timestamps]
	
	def is_allowed(self, ip_address: str) -> bool:
		"""Check if request is allowed from this IP."""
		now = datetime.now(timezone.utc)
		cutoff = now - timedelta(seconds=self.window_seconds)
		
		# Clean old requests
		self.requests[ip_address] = [
			ts for ts in self.requests[ip_address]
			if ts > cutoff
		]
		
		# Check limit
		if len(self.requests[ip_address]) >= self.max_requests:
			return False
		
		# Record new request
		self.requests[ip_address].append(now)
		return True


def rate_limit_handler():
	"""Decorator factory that uses the app's rate limiter."""
	def decorator(f):
		@wraps(f)
		def decorated_function(*args, **kwargs):
			from flask import current_app
			client_ip = request.remote_addr or "unknown"
			if not current_app.rate_limiter.is_allowed(client_ip):
				return jsonify({
					"accepted": False,
					"error": "Rate limit exceeded (DOS protection)",
					"retry_after": current_app.rate_limiter.window_seconds,
				}), 429  # Too Many Requests
			return f(*args, **kwargs)
		return decorated_function
	return decorator


def rate_limit(limiter: RateLimiter, max_requests: int = 100):
	"""Decorator for rate limiting endpoints."""
	def decorator(f):
		@wraps(f)
		def decorated_function(*args, **kwargs):
			client_ip = request.remote_addr or "unknown"
			if not limiter.is_allowed(client_ip):
				return jsonify({
					"accepted": False,
					"error": "Rate limit exceeded (DOS protection)",
					"retry_after": limiter.window_seconds,
				}), 429  # Too Many Requests
			return f(*args, **kwargs)
		return decorated_function
	return decorator


# OpenAPI specification for API documentation
OPENAPI_SPEC = {
	"openapi": "3.0.0",
	"info": {
		"title": "PQDrive OTA Security Demo API",
		"version": "1.0.0",
		"description": "REST API for post-quantum OTA verification, charger security, and threat injection",
	},
	"servers": [{"url": "http://localhost:5000", "description": "Development server"}],
	"paths": {
		"/api/report": {
			"get": {
				"summary": "Get full demo report",
				"description": "Returns comprehensive report with all scenarios, metrics, and threat model",
				"responses": {
					"200": {
						"description": "Full demo report",
						"content": {"application/json": {"schema": {"type": "object"}}},
					}
				},
			}
		},
		"/api/scenarios": {
			"get": {
				"summary": "Get scenarios and metrics",
				"description": "Returns scenarios list and performance metrics",
				"responses": {
					"200": {
						"description": "Scenarios and metrics",
						"content": {"application/json": {"schema": {"type": "object"}}},
					}
				},
			}
		},
		"/api/run-scenario": {
			"post": {
				"summary": "Run single scenario",
				"description": "Execute a scenario with optional vehicle state overrides and threat injection",
				"requestBody": {
					"required": True,
					"content": {
						"application/json": {
							"schema": {
								"type": "object",
								"properties": {
									"scenario_name": {"type": "string", "description": "Name of scenario to run"},
									"vehicle_state": {"type": "object", "description": "Optional vehicle state overrides"},
									"threat_injection": {"type": "string", "enum": ["bit-flip", "downgrade", "tamper-signature"], "description": "Optional threat to inject"},
								},
								"required": ["scenario_name"],
							}
						}
					},
				},
				"responses": {
					"200": {
						"description": "Scenario result",
						"content": {"application/json": {"schema": {"type": "object"}}},
					}
				},
			}
		},
		"/api/presets": {
			"get": {
				"summary": "Get vehicle state presets",
				"description": "Returns available predefined vehicle state configurations",
				"responses": {
					"200": {
						"description": "Vehicle state presets",
						"content": {"application/json": {"schema": {"type": "object"}}},
					}
				},
			}
		},
		"/api/audit-log": {
			"get": {
				"summary": "Get audit log",
				"description": "Returns security audit log events",
				"responses": {
					"200": {
						"description": "Audit log entries",
						"content": {"application/json": {"schema": {"type": "array"}}},
					}
				},
			}
		},
	},
}


def create_app() -> Flask:
	app = Flask(__name__, template_folder="templates", static_folder="static")
	app.config["JSON_SORT_KEYS"] = False
	app.config["SECRET_KEY"] = "pqdrive-demo-key"
	
	# SECURITY FIX (Phase 7C): Initialize rate limiter for DOS protection
	# Allow 100 requests per 60 seconds per IP address
	app.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
	
	# Initialize SocketIO for real-time updates
	socketio = SocketIO(app, cors_allowed_origins="*")
	
	# Initialize global recovery manager for audit logging
	app.recovery_manager = RecoveryManager()
	app.socketio = socketio
	
	# SECURITY FIX: Initialize real OTA infrastructure (not mocks)
	from core.kyber import generate_keypair as kyber_keygen
	from core.dilithium import generate_keypair as dilithium_keygen
	from core.pipeline import OTAVerificationPipeline
	from vehicle.ota_server import OTAServer
	from vehicle.gateway import VehicleGateway
	
	# Generate keypairs for demo (in production: load from HSM)
	vehicle_pub, vehicle_priv = kyber_keygen()
	server_pub, server_priv = dilithium_keygen()
	
	# Initialize real components
	app.ota_server = OTAServer(server_priv, server_pub, vehicle_pub)
	app.verification_pipeline = OTAVerificationPipeline(vehicle_pub, vehicle_priv, server_pub)
	app.vehicle_gateway = VehicleGateway(vehicle_pub, vehicle_priv, server_pub)
	
	# Store keys for pipeline verification
	app.vehicle_public_key = vehicle_pub
	app.vehicle_private_key = vehicle_priv
	app.server_public_key = server_pub
	
	# Store unified ECU policy (single source of truth)
	app.config["ecu_policy"] = {
		"adas_ecu": {"max_speed": 0, "min_battery": 20, "charging_ok": True},
		"powertrain_ecu": {"max_speed": 0, "min_battery": 20, "charging_ok": False},
		"braking_ecu": {"max_speed": 0, "min_battery": 25, "charging_ok": True},
		"steering_ecu": {"max_speed": 5, "min_battery": 15, "charging_ok": True},
		"maps_ecu": {"max_speed": 150, "min_battery": 5, "charging_ok": True},
	}

	@app.get("/")
	def index() -> str:
		return render_template("index.html")

	@app.get("/health")
	def health() -> tuple[dict, int]:
		"""Health check endpoint for container orchestration (K8s, Docker)."""
		return jsonify({"status": "healthy", "service": "pqdrive-dashboard"}), 200

	@app.get("/api/report")
	@rate_limit_handler()
	def report() -> tuple[dict, int]:
		return jsonify(build_demo_report()), 200

	@app.get("/api/scenarios")
	@rate_limit_handler()
	def scenarios() -> tuple[dict, int]:
		report = build_demo_report()
		return jsonify({"scenarios": report["scenarios"], "metrics": report["metrics"]}), 200

	@app.post("/api/run-scenario")
	@rate_limit_handler()
	def run_scenario() -> tuple[dict, int]:
		"""Run a single scenario with optional vehicle state overrides and threat injection."""
		data = request.get_json() or {}
		scenario_name = data.get("scenario_name", "Legitimate OTA")
		vehicle_state = data.get("vehicle_state", {})
		threat_injection = data.get("threat_injection")

		result = run_single_scenario(scenario_name, vehicle_state, threat_injection)
		
		# Log scenario execution to audit log
		app.recovery_manager.log_event(
			"scenario_executed",
			{
				"scenario_name": scenario_name,
				"accepted": result.get("accepted", False),
				"failed_at": result.get("failed_at"),
				"threat_injection": threat_injection,
				"duration_ms": result.get("duration_ms", 0),
			}
		)
		
		return jsonify(result), 200

	@app.get("/api/presets")
	@rate_limit_handler()
	def presets() -> tuple[dict, int]:
		"""Return vehicle state presets for the dashboard."""
		return jsonify(get_vehicle_state_presets()), 200

	@app.post("/api/parse-firmware")
	def parse_firmware() -> tuple[dict, int]:
		"""Parse firmware JSON and extract version/metadata."""
		data = request.get_json() or {}
		payload = data.get("payload", "").strip()
		
		if not payload:
			return jsonify({"error": "No payload provided"}), 400

		parsed = parse_firmware_payload(payload)
		if not parsed.get("valid"):
			return jsonify(parsed), 400

		return jsonify(
			{
				"ecu_id": parsed.get("ecu_id"),
				"hw": parsed.get("hw"),
				"version": parsed.get("sw"),
				"build": parsed.get("build"),
				"timestamp": parsed.get("timestamp"),
				"modules": parsed.get("modules", []),
				"patches": parsed.get("patches", []),
				"payload_preview": payload[:150] + ("..." if len(payload) > 150 else ""),
			}
		), 200

	@app.post("/api/run-json-scenario")
	def run_json_scenario() -> tuple[dict, int]:
		"""Run OTA with payload parsing, scenario classification, and pipeline verification."""
		data = request.get_json() or {}
		payload = data.get("payload", "").strip()
		vehicle_state_overrides = data.get("vehicle_state", {})
		
		if not payload:
			return jsonify({"error": "No firmware payload provided"}), 400

		classification = classify_payload(payload)
		parsed = classification.get("parsed", {})
		firmware_version = parsed.get("sw")
		firmware_ecu_id = parsed.get("ecu_id")
		target_ecu = classification.get("target_ecu", "maps_ecu")
		delivery_context = classification.get("delivery_context", {})

		def _trace_ok(trace: list[dict], stage_name: str) -> bool:
			for entry in trace:
				if entry.get("stage") == stage_name:
					return bool(entry.get("ok", False))
			return False

		delivery_gate = evaluate_delivery_gate(vehicle_state_overrides, classification, app.config.get("ecu_policy", {}))
		result_obj = {
			"delivery_gate_ok": delivery_gate.get("ok", False),
			"freshness_ok": False,
			"kyber_ok": False,
			"dilithium_ok": False,
			"hash_ok": False,
			"version_ok": False,
			"ecu_validation_ok": False,
		}

		if classification.get("scenario") == "invalid_payload":
			return jsonify({
				"result": result_obj,
				"all_passed": False,
				"accepted": False,
				"failed_at": "payload_parse",
				"reason": parsed.get("error", "Invalid payload format"),
				"classification": classification,
				"delivery_gate": delivery_gate,
			}), 400

		if not delivery_gate.get("ok", False):
			app.recovery_manager.log_event("ota_rejected", {
				"reason": "delivery_gate_check",
				"firmware_ecu": firmware_ecu_id,
				"status_reason": delivery_gate.get("reason"),
				"delivery_context": delivery_context,
			})
			return jsonify({
				"result": result_obj,
				"all_passed": False,
				"accepted": False,
				"failed_at": "delivery_gate",
				"reason": delivery_gate.get("reason"),
				"firmware_version": firmware_version,
				"firmware_ecu": firmware_ecu_id,
				"target_ecu": target_ecu,
				"classification": classification,
				"delivery_gate": delivery_gate,
				"verification_trace": [
					{"stage": "delivery_gate", "ok": False, "reason": delivery_gate.get("reason")}
				],
			}), 200
		
		# Stage 2-5: CRITICAL FIX - Call real OTA verification pipeline
		# Don't just approve based on format checks - verify cryptography
		try:
			# Use OTA server to create properly signed and encrypted package
			payload_bytes = payload.encode()
			profile_meta = classification.get("profile", {})
			if classification.get("scenario") == "rollback_attack":
				baseline_current = profile_meta.get("legit_sw", "2.0.0")
			else:
				baseline_current = profile_meta.get("rollback_sw", "1.0.0")
			if classification.get("scenario") == "rogue_charger":
				from core import dilithium as pq_dilithium

				attacker_public_key, attacker_private_key = pq_dilithium.generate_keypair()
				_ = attacker_public_key
				update_package = app.ota_server.prepare_update(
					payload=payload_bytes,
					current_version=baseline_current,
					new_version=firmware_version or "1.0.0",
					target_ecu=target_ecu,
				)
				update_package["signature"] = pq_dilithium.sign(attacker_private_key, payload_bytes).hex()
				update_package["source"] = delivery_context.get("source", "charging_network")
			else:
				update_package = app.ota_server.prepare_update(
					payload=payload_bytes,
					current_version=baseline_current,
					new_version=firmware_version or "1.0.0",
					target_ecu=target_ecu,
				)
				update_package["source"] = delivery_context.get("source", "legitimate_ota_server")

			update_package["delivery_channel"] = delivery_context.get("delivery_channel")
			update_package["vehicle_state"] = vehicle_state_overrides

			pipeline_result = app.verification_pipeline.run(update_package)
			result_obj.update({
				"freshness_ok": _trace_ok(pipeline_result.get("verification_trace", []), "freshness"),
				"kyber_ok": pipeline_result.get("kyber_ok", False),
				"dilithium_ok": pipeline_result.get("dilithium_ok", False),
				"hash_ok": pipeline_result.get("hash_ok", False),
				"version_ok": pipeline_result.get("version_ok", False),
			})

			ecu_validation_ok = bool(target_ecu and app.vehicle_gateway.ecu_manager.is_valid_ecu_target(target_ecu))
			if ecu_validation_ok:
				result_obj["ecu_validation_ok"] = True
			else:
				result_obj["ecu_validation_ok"] = False
				verification_trace = list(pipeline_result.get("verification_trace", []))
				verification_trace.append({"stage": "ecu_validation", "ok": False, "reason": f"Invalid ECU target: {target_ecu}"})
				app.recovery_manager.log_event("ota_rejected", {
					"reason": "ecu_validation_failed",
					"failed_at": "ecu_validation",
					"firmware_ecu": firmware_ecu_id,
					"firmware_version": firmware_version,
				})
				return jsonify({
					"result": result_obj,
					"all_passed": False,
					"accepted": False,
					"failed_at": "ecu_validation",
					"reason": f"Invalid ECU target: {target_ecu}",
					"firmware_version": firmware_version,
					"firmware_ecu": firmware_ecu_id,
					"target_ecu": target_ecu,
					"classification": classification,
					"delivery_gate": delivery_gate,
					"verification_trace": verification_trace,
				}), 200
			
			# Update result_obj with actual cryptographic verification results
			
			# If pipeline says "no", we say "no" (fail-safe design)
			if not pipeline_result.get("all_passed", False):
				app.recovery_manager.log_event("ota_rejected", {
					"reason": "cryptographic_verification_failed",
					"failed_at": pipeline_result.get("failed_at"),
					"firmware_ecu": firmware_ecu_id,
					"firmware_version": firmware_version,
				})
				return jsonify({
					"result": result_obj,
					"all_passed": False,
					"accepted": False,
					"failed_at": pipeline_result.get("failed_at", "unknown"),
					"reason": f"Cryptographic verification failed at stage: {pipeline_result.get('failed_at')}",
					"firmware_version": firmware_version,
					"firmware_ecu": firmware_ecu_id,
					"target_ecu": target_ecu,
					"classification": classification,
					"delivery_gate": delivery_gate,
					"verification_trace": pipeline_result.get("verification_trace", []),
				}), 200

			verification_trace = list(pipeline_result.get("verification_trace", []))
			verification_trace.append({"stage": "ecu_validation", "ok": True, "reason": f"ECU target {target_ecu} validated"})
			
		except Exception as e:
			# Security: Any verification error means reject (fail-safe)
			app.recovery_manager.log_event("ota_error", {
				"error": str(e),
				"firmware_ecu": firmware_ecu_id,
				"firmware_version": firmware_version,
			})
			return jsonify({
				"result": result_obj,
				"all_passed": False,
				"accepted": False,
				"failed_at": "verification_error",
				"reason": f"Verification error: {str(e)}",
				"firmware_version": firmware_version,
				"firmware_ecu": firmware_ecu_id,
				"target_ecu": target_ecu,
				"classification": classification,
				"delivery_gate": delivery_gate,
			}), 200
		
		# All checks passed - OTA update approved
		app.recovery_manager.log_event("ota_accepted", {
			"firmware_ecu": firmware_ecu_id,
			"firmware_version": firmware_version,
			"delivery_context": delivery_context,
		})
		
		return jsonify({
			"result": result_obj,
			"all_passed": True,
			"failed_at": None,
			"accepted": True,
			"firmware_version": firmware_version,
			"firmware_ecu": firmware_ecu_id,
			"target_ecu": target_ecu,
			"target_ecu_updated": True,
			"classification": classification,
			"delivery_gate": delivery_gate,
			"verification_trace": verification_trace,
		}), 200

	@app.get("/api/audit-log")
	def audit_log() -> tuple[list, int]:
		"""Return security audit log events from the recovery manager."""
		return jsonify(app.recovery_manager.get_audit_log()), 200

	@app.get("/api/education")
	def education() -> tuple[dict, int]:
		"""Return educational content about cryptography and security principles."""
		return jsonify({
			"principles": {
				"kyber_kem": {
					"title": "Kyber Key Encapsulation Mechanism",
					"category": "Post-Quantum Cryptography",
					"description": "NIST-standardized lattice-based key encapsulation that's safe against quantum computers",
					"purpose": "Establishes quantum-resistant shared secrets between OTA server and vehicle",
					"security_property": "IND-CCA2 secure - protects against chosen-ciphertext attacks",
					"why_it_matters": "Classical RSA/ECDH would be broken by future quantum computers. Kyber provides future-proof security.",
				},
				"dilithium_signature": {
					"title": "Dilithium Digital Signatures",
					"category": "Post-Quantum Cryptography",
					"description": "NIST-standardized lattice-based digital signature algorithm",
					"purpose": "Proves firmware origin and integrity, prevents code injection",
					"security_property": "SUF-CMA secure - unforgeable even with chosen message attacks",
					"why_it_matters": "Ensures OTA updates come from legitimate OTA servers, not rogue sources",
				},
				"sha3_hash": {
					"title": "SHA3-256 Cryptographic Hash",
					"category": "Symmetric Cryptography",
					"description": "Quantum-resistant cryptographic hash function (unaffected by quantum computers)",
					"purpose": "Provides bit-level integrity checking of firmware payload",
					"security_property": "Pre-image resistant - impossible to forge data with same hash",
					"why_it_matters": "Single bit-flip in firmware is detected and rejected",
				},
				"replay_defense": {
					"title": "Replay Attack Prevention",
					"category": "Protocol Security",
					"description": "Uses nonce/timestamp to ensure each OTA can only be used once",
					"purpose": "Prevents attackers from replaying old OTA updates",
					"security_property": "Ensures freshness of authentication material",
					"why_it_matters": "Attackers can't use captured network traffic twice",
				},
				"version_monotonicity": {
					"title": "Rollback Prevention",
					"category": "Software Security",
					"description": "Firmware version must always increase, never decrease",
					"purpose": "Blocks downgrade attacks to vulnerable firmware versions",
					"security_property": "Version ordering is strictly enforced and logged",
					"why_it_matters": "Even if old firmware has known CVEs, attacker can't downgrade to it",
				},
				"vehicle_state_gating": {
					"title": "Vehicle Safety Gating",
					"category": "Safety-Critical Systems",
					"description": "OTA only accepted when vehicle is safe (not moving, not charging, cool)",
					"purpose": "Prevents firmware corruption due to power loss during update",
					"security_property": "Ensures reliable update process with redundant power sources",
					"why_it_matters": "Update failures on highway could cause catastrophic loss of control",
				},
				"multi_layer_verification": {
					"title": "Defense-in-Depth",
					"category": "Security Architecture",
					"description": "Multiple independent checks must all pass for update acceptance",
					"purpose": "If one defense is bypassed, others remain effective",
					"security_property": "Fail-safe design - rejection is default, acceptance requires all checks",
					"why_it_matters": "No single vulnerability can compromise the entire system",
				},
			},
			"threat_model": {
				"entry_points": [
					"Wireless network interfaces (LTE, 5G, WiFi)",
					"Charging station data lines (DC/AC chargers)",
					"OBD-II diagnostic port",
					"V2V/V2X communication",
				],
				"attack_scenarios": [
					{
						"name": "Network Eavesdropping",
						"attack": "Attacker intercepts OTA update in transit",
						"defense": "Kyber KEM + encryption prevents plaintext access",
					},
					{
						"name": "Code Injection",
						"attack": "Attacker substitutes malicious firmware",
						"defense": "Dilithium signature proves firmware origin",
					},
					{
						"name": "Bit Flip Corruption",
						"attack": "Attacker flips single bit in firmware (radio interference)",
						"defense": "SHA3-256 integrity check detects any modification",
					},
					{
						"name": "Downgrade Attack",
						"attack": "Attacker forces installation of older firmware with known CVEs",
						"defense": "Version monotonicity check blocks all downgrades",
					},
					{
						"name": "Replay Attack",
						"attack": "Attacker captures and repeats old valid OTA update",
						"defense": "Nonce-based replay protection prevents reuse",
					},
					{
						"name": "Juice-Jacking at Charger",
						"attack": "Rogue charger tries to push malicious firmware during charging",
						"defense": "Vehicle state gating + charger authentication prevents exploit",
					},
				],
			},
		}), 200

	@app.get("/api/run-scenario")
	def api_get_run_scenario() -> tuple[dict, int]:
		"""GET endpoint info for running scenarios."""
		return jsonify({
			"message": "Use POST /api/run-scenario to execute a scenario",
			"example_payload": {
				"scenario_name": "Legitimate OTA",
				"vehicle_state": {
					"speed_kph": 0,
					"battery_soc": 68,
					"temperature_c": 31,
					"data_link_locked": True,
					"charging_active": True,
				},
				"threat_injection": "bit-flip"
			}
		}), 200

	@app.get("/api/docs")
	def docs_json() -> tuple[dict, int]:
		"""Return OpenAPI specification."""
		return jsonify(OPENAPI_SPEC), 200

	@app.get("/api/docs/html")
	def docs_html() -> str:
		"""Return API documentation as HTML."""
		html = """
		<!DOCTYPE html>
		<html>
		<head>
			<title>PQDrive API Documentation</title>
			<style>
				body { font-family: -apple-system, system-ui, sans-serif; line-height: 1.6; color: #333; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
				h1, h2 { color: #29d3b7; }
				.endpoint { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #29d3b7; }
				.method { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; margin-right: 8px; }
				.method.get { background: #0066cc; }
				.method.post { background: #28a745; }
				code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
				pre { background: #f0f0f0; padding: 12px; border-radius: 4px; overflow: auto; }
			</style>
		</head>
		<body>
			<h1>PQDrive OTA Security Demo - API Documentation</h1>
			<p>This API enables running OTA security scenarios with threat injection, vehicle state simulation, and audit logging.</p>
			
			<div class="endpoint">
				<span class="method get">GET</span><h2>/api/report</h2>
				<p>Returns the full demo report with all scenarios, metrics, threat model, and recommendations.</p>
				<p><strong>Response:</strong> Full report object including scenarios, audit log, and metrics.</p>
			</div>
			
			<div class="endpoint">
				<span class="method get">GET</span><h2>/api/scenarios</h2>
				<p>Returns scenarios list and performance metrics.</p>
				<p><strong>Response:</strong> Object with <code>scenarios</code> array and <code>metrics</code> object.</p>
			</div>
			
			<div class="endpoint">
				<span class="method get">GET</span><h2>/api/presets</h2>
				<p>Returns available vehicle state presets.</p>
				<p><strong>Response:</strong> Object mapping preset names to vehicle state objects.</p>
				<pre>{"Parked & Charging": {"speed_kph": 0, "battery_soc": 68, ...}, ...}</pre>
			</div>
			
			<div class="endpoint">
				<span class="method post">POST</span><h2>/api/run-scenario</h2>
				<p>Execute a scenario with optional vehicle state overrides and threat injection.</p>
				<p><strong>Request body:</strong></p>
				<pre>{"scenario_name": "Legitimate OTA", "vehicle_state": {...}, "threat_injection": "bit-flip"}</pre>
				<p><strong>Threat injection types:</strong> bit-flip, downgrade, tamper-signature</p>
				<p><strong>Response:</strong> Scenario result with acceptance status, latency, and audit trail.</p>
			</div>
			
			<div class="endpoint">
				<span class="method get">GET</span><h2>/api/audit-log</h2>
				<p>Returns audit log entries including all OTA decisions and security events.</p>
				<p><strong>Response:</strong> Array of audit log entries with timestamps and signatures.</p>
			</div>
			
			<div class="endpoint">
				<span class="method get">GET</span><h2>/api/docs</h2>
				<p>Returns this API specification in OpenAPI JSON format.</p>
			</div>
		</body>
		</html>
		"""
		return html

	return app


app = create_app()
socketio = app.socketio


if __name__ == "__main__":
	socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)