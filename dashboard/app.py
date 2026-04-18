"""Flask dashboard for the OTA and charger security demo."""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from core.demo_runner import build_demo_report, run_single_scenario, get_vehicle_state_presets
from vehicle.recovery import RecoveryManager


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
	
	# Initialize global recovery manager for audit logging
	app.recovery_manager = RecoveryManager()

	@app.get("/")
	def index() -> str:
		return render_template("index.html")

	@app.get("/api/report")
	def report() -> tuple[dict, int]:
		return jsonify(build_demo_report()), 200

	@app.get("/api/scenarios")
	def scenarios() -> tuple[dict, int]:
		report = build_demo_report()
		return jsonify({"scenarios": report["scenarios"], "metrics": report["metrics"]}), 200

	@app.post("/api/run-scenario")
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
	def presets() -> tuple[dict, int]:
		"""Return vehicle state presets for the dashboard."""
		return jsonify(get_vehicle_state_presets()), 200

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


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000, debug=True)