from core.payload_classifier import classify_payload, evaluate_delivery_gate, parse_firmware_payload


def test_parse_payload_extracts_core_fields() -> None:
	payload = (
		"ECU_ID:ADAS-3.2 | HW:REV-C | SW:2.0.0 | BUILD:20240318-a4f2c1 | "
		"REGION:EU | MODULES:LANE_KEEP_v4,COLLISION_WARN_v3 | "
		"PATCHES:CVE-2024-3821,CVE-2024-4102 | TS:2024-03-18T09:14:22Z"
	)
	parsed = parse_firmware_payload(payload)

	assert parsed["valid"] is True
	assert parsed["ecu_id"] == "ADAS-3.2"
	assert parsed["sw"] == "2.0.0"
	assert parsed["modules"] == ["LANE_KEEP_v4", "COLLISION_WARN_v3"]
	assert parsed["patches"] == ["CVE-2024-3821", "CVE-2024-4102"]


def test_classify_detects_rogue_sentinel_version() -> None:
	payload = (
		"ECU_ID:PWRT-5.1 | HW:REV-B | SW:9.9.9 | BUILD:20240318-b8e3d7 | "
		"REGION:EU | MODULES:TORQUE_CTL_v6,REGEN_BRAKE_v4,THERMAL_MGMT_v3 | "
		"PATCHES:CVE-2024-5501 | TS:2024-03-18T09:16:04Z"
	)
	classification = classify_payload(payload)

	assert classification["scenario"] == "rogue_charger"
	assert classification["execution_mode"] == "force_rogue_source"
	assert "sentinel_sw_9_9_9" in classification["iocs"]


def test_classify_detects_rollback() -> None:
	payload = (
		"ECU_ID:BODY-2.0 | HW:REV-A | SW:1.0.0 | BUILD:20230912-h7c5e1 | "
		"REGION:EU | MODULES:DOOR_LOCK_v2,WINDOW_CTL_v1,LIGHT_MGR_v3 | "
		"TS:2023-09-12T11:08:44Z"
	)
	classification = classify_payload(payload)

	assert classification["scenario"] == "rollback_attack"
	assert classification["execution_mode"] == "version_guard"
	assert "version_regression" in classification["iocs"]


def test_classify_marks_chassis_clone_as_medium_confidence() -> None:
	payload = (
		"ECU_ID:CHAS-4.0 | HW:REV-D | SW:2.0.0 | BUILD:20240318-d7c4b5 | "
		"REGION:EU | MODULES:ABS_CTL_v5,STABILITY_v4,STEER_ASSIST_v3,SUSP_CTL_v2 | "
		"PATCHES:CVE-2024-6612 | TS:2024-03-18T09:20:33Z"
	)
	classification = classify_payload(payload)

	assert classification["scenario"] == "legitimate_or_metadata_clone"
	assert classification["confidence"] == "medium"
	assert classification["threat_classification"] == "PAYLOAD_TAMPER"
	assert "stealth_clone_possible" in classification["iocs"]


def test_delivery_gate_rejects_rogue_charger_when_idle() -> None:
	payload = (
		"ECU_ID:ADAS-3.2 | HW:REV-C | SW:9.9.9 | BUILD:20240318-a4f2c1 | "
		"REGION:EU | MODULES:LANE_KEEP_v4,COLLISION_WARN_v3,BLIND_SPOT_v2,SIGN_RECOG_v5 | "
		"PATCHES:CVE-2024-3821,CVE-2024-4102 | TS:2024-03-18T09:14:22Z"
	)
	classification = classify_payload(payload)
	gate = evaluate_delivery_gate(
		{"speed_kph": 0, "battery_soc": 68, "charging_active": False, "data_link_locked": True},
		classification,
		{"adas_ecu": {"max_speed": 0, "min_battery": 20, "charging_ok": True}},
	)

	assert gate["ok"] is False
	assert gate["failed_at"] == "delivery_gate"
	assert gate["source"] == "charging_network"


def test_delivery_gate_allows_rogue_charger_when_charging() -> None:
	payload = (
		"ECU_ID:ADAS-3.2 | HW:REV-C | SW:9.9.9 | BUILD:20240318-a4f2c1 | "
		"REGION:EU | MODULES:LANE_KEEP_v4,COLLISION_WARN_v3,BLIND_SPOT_v2,SIGN_RECOG_v5 | "
		"PATCHES:CVE-2024-3821,CVE-2024-4102 | TS:2024-03-18T09:14:22Z"
	)
	classification = classify_payload(payload)
	gate = evaluate_delivery_gate(
		{"speed_kph": 0, "battery_soc": 68, "charging_active": True, "data_link_locked": True},
		classification,
		{"adas_ecu": {"max_speed": 0, "min_battery": 20, "charging_ok": True}},
	)

	assert gate["ok"] is True
	assert gate["source_matches_state"] is True


def test_delivery_gate_allows_powertrain_charging_updates() -> None:
	payload = (
		"ECU_ID:PWRT-5.1 | HW:REV-B | SW:9.9.9 | BUILD:20240318-b8e3d7 | "
		"REGION:EU | MODULES:TORQUE_CTL_v6,REGEN_BRAKE_v4,THERMAL_MGMT_v3 | "
		"PATCHES:CVE-2024-5501 | TS:2024-03-18T09:16:04Z"
	)
	classification = classify_payload(payload)
	gate = evaluate_delivery_gate(
		{"speed_kph": 0, "battery_soc": 68, "charging_active": True, "data_link_locked": True},
		classification,
		{"powertrain_ecu": {"max_speed": 0, "min_battery": 20, "charging_ok": True}},
	)

	assert gate["ok"] is True
	assert gate["target_ecu"] == "powertrain_ecu"


def test_payload_tamper_forces_content_verification_failure() -> None:
	from dashboard.app import app

	payload = (
		"ECU_ID:BODY-2.0 | HW:REV-A | SW:2.0.0 | BUILD:20240318-c1f9a2 | "
		"REGION:EU | MODULES:DOOR_LOCK_v3,WINDOW_CTL_v2,LIGHT_MGR_v4,SENSOR_FUSION_v2 | "
		"TS:2024-03-18T09:18:11Z"
	)
	client = app.test_client()
	result = client.post(
		"/api/run-json-scenario",
		json={
			"payload": payload,
			"scenario_hint": "tamper",
			"vehicle_state": {"speed_kph": 0, "battery_soc": 68, "temperature_c": 31, "charging_active": False, "data_link_locked": True},
		},
	).get_json()

	assert result["classification"]["threat_classification"] == "PAYLOAD_TAMPER"
	assert result["failed_at"] in {"dilithium", "hash"}
	assert result["delivery_gate"]["ok"] is True