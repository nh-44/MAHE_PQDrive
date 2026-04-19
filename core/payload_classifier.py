"""Parse and classify pipe-delimited firmware payloads for OTA threat analysis."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ECUProfile:
	"""Canonical metadata baseline for each ECU family in demo datasets."""

	ecu_id: str
	hardware_rev: str
	legit_sw: str
	rogue_sw: str
	rollback_sw: str
	legit_build: str
	legit_ts: str
	risk: str
	target_ecu: str


@dataclass(frozen=True)
class DeliveryContext:
	"""How the payload is expected to reach the vehicle."""

	source: str
	delivery_channel: str
	requires_charging_state: bool


LEGITIMATE_SOURCE = "legitimate_ota_server"
ROGUE_SOURCE = "charging_network"
WIRELESS_CHANNEL = "wireless_telematics"
CHARGER_CHANNEL = "charger_interface"

THREAT_LEGITIMATE = "LEGITIMATE"
THREAT_ROGUE_VERSION = "ROGUE_VERSION"
THREAT_ROLLBACK = "ROLLBACK"
THREAT_PAYLOAD_TAMPER = "PAYLOAD_TAMPER"

BODY_HEX_FIELDS = ("BODY_HEX", "PAYLOAD_BODY_HEX", "PAYLOAD_HEX", "CONTENT_HEX")
BODY_B64_FIELDS = ("BODY_B64", "PAYLOAD_BODY_B64", "PAYLOAD_B64", "CONTENT_B64")
BODY_RAW_FIELDS = ("BODY_RAW", "PAYLOAD_BODY_RAW", "CONTENT_RAW", "BODY")

# Trust store keyed by BUILD id: expected SHA-256 over the raw firmware body bytes.
BUILD_CONTENT_TRUST_STORE: dict[str, dict[str, Any]] = {
	"20240318-a4f2c1": {
		"expected_body_sha256": "34d086542734c61e52a2a6b19b9f567fd466a2f7eab90453abc93fab3b5e8ca7",
		"expected_modules": ["LANE_KEEP_v4", "COLLISION_WARN_v3", "BLIND_SPOT_v2", "SIGN_RECOG_v5"],
	},
	"20240318-b8e3d7": {
		"expected_body_sha256": "25aff0b5dda60cbe84a5d6bf27eb134f12d21f8289f5b1c5fc3d717e49378400",
		"expected_modules": ["TORQUE_CTL_v6", "REGEN_BRAKE_v4", "THERMAL_MGMT_v3"],
	},
	"20240318-c1f9a2": {
		"expected_body_sha256": "d2eb566d49e2921560a170bbea78c9f7094441a9a3c9e1f378ad7f19750b9862",
		"expected_modules": ["DOOR_LOCK_v3", "WINDOW_CTL_v2", "LIGHT_MGR_v4", "SENSOR_FUSION_v2"],
	},
	"20240318-d7c4b5": {
		"expected_body_sha256": "7ddbac96f34b370c673822f3e8c82f365d06f4318f5165e99bcaa1e3dc59b051",
		"expected_modules": ["ABS_CTL_v5", "STABILITY_v4", "STEER_ASSIST_v3", "SUSP_CTL_v2"],
	},
	"20240318-e2a7f8": {
		"expected_body_sha256": "b76f83836c79faf1c09470606ccb8fb3d721f24dff18b173c137c01c296a9219",
		"expected_modules": ["MAP_CORE_v8", "NAV_UI_v5", "VOICE_ASSIST_v4", "MEDIA_SYNC_v6"],
	},
}


ECU_PROFILES: dict[str, ECUProfile] = {
	"ADAS-3.2": ECUProfile(
		ecu_id="ADAS-3.2",
		hardware_rev="REV-C",
		legit_sw="2.0.0",
		rogue_sw="9.9.9",
		rollback_sw="1.0.0",
		legit_build="20240318-a4f2c1",
		legit_ts="2024-03-18T09:14:22Z",
		risk="CRITICAL",
		target_ecu="adas_ecu",
	),
	"PWRT-5.1": ECUProfile(
		ecu_id="PWRT-5.1",
		hardware_rev="REV-B",
		legit_sw="2.0.0",
		rogue_sw="9.9.9",
		rollback_sw="1.0.0",
		legit_build="20240318-b8e3d7",
		legit_ts="2024-03-18T09:16:04Z",
		risk="CRITICAL",
		target_ecu="powertrain_ecu",
	),
	"BODY-2.0": ECUProfile(
		ecu_id="BODY-2.0",
		hardware_rev="REV-A",
		legit_sw="2.0.0",
		rogue_sw="9.9.9",
		rollback_sw="1.0.0",
		legit_build="20240318-c1f9a2",
		legit_ts="2024-03-18T09:18:11Z",
		risk="HIGH",
		target_ecu="steering_ecu",
	),
	"CHAS-4.0": ECUProfile(
		ecu_id="CHAS-4.0",
		hardware_rev="REV-D",
		legit_sw="2.0.0",
		rogue_sw="2.0.0",  # Stealthy metadata-clone case in supplied dataset
		rollback_sw="1.0.0",
		legit_build="20240318-d7c4b5",
		legit_ts="2024-03-18T09:20:33Z",
		risk="CRITICAL",
		target_ecu="braking_ecu",
	),
	"INFO-1.8": ECUProfile(
		ecu_id="INFO-1.8",
		hardware_rev="REV-A",
		legit_sw="2.0.0",
		rogue_sw="9.9.9",
		rollback_sw="1.0.0",  # Dataset anomaly has rollback payload at 9.9.9
		legit_build="20240318-e2a7f8",
		legit_ts="2024-03-18T09:22:47Z",
		risk="HIGH",
		target_ecu="maps_ecu",
	),
}


def _as_version_tuple(value: str) -> tuple[int, ...]:
	parts = value.split(".")
	return tuple(int(p) for p in parts)


def parse_firmware_payload(payload_text: str) -> dict[str, Any]:
	"""Parse pipe-delimited payload into normalized key/value metadata."""
	payload_text = payload_text.strip()
	if not payload_text:
		return {"valid": False, "error": "empty payload"}

	fields: dict[str, str] = {}
	for chunk in payload_text.split("|"):
		part = chunk.strip()
		if not part or ":" not in part:
			continue
		key, value = part.split(":", 1)
		fields[key.strip().upper()] = value.strip()

	ecu_id = fields.get("ECU_ID")
	hw = fields.get("HW")
	sw = fields.get("SW")
	build = fields.get("BUILD")
	ts = fields.get("TS")
	modules_raw = fields.get("MODULES", "")
	patches_raw = fields.get("PATCHES", "")

	if not ecu_id or not sw:
		return {
			"valid": False,
			"error": "payload must include ECU_ID and SW fields",
			"fields": fields,
		}

	modules = [m.strip() for m in modules_raw.split(",") if m.strip()]
	patches = [p.strip() for p in patches_raw.split(",") if p.strip()]

	parsed: dict[str, Any] = {
		"valid": True,
		"raw": payload_text,
		"fields": fields,
		"ecu_id": ecu_id,
		"hw": hw,
		"sw": sw,
		"build": build,
		"timestamp": ts,
		"modules": modules,
		"patches": patches,
	}

	if ts:
		try:
			datetime.fromisoformat(ts.replace("Z", "+00:00"))
		except ValueError:
			parsed["timestamp_warning"] = "timestamp is not RFC3339-compatible"

	return parsed


def extract_raw_payload_body_bytes(parsed: dict[str, Any]) -> bytes | None:
	"""Extract raw firmware body bytes from parsed payload fields.

	Only explicit body/content fields are treated as raw payload body.
	"""
	fields = parsed.get("fields", {})

	for key in BODY_HEX_FIELDS:
		value = fields.get(key)
		if not value:
			continue
		try:
			return bytes.fromhex(value)
		except ValueError:
			return None

	for key in BODY_B64_FIELDS:
		value = fields.get(key)
		if not value:
			continue
		try:
			return base64.b64decode(value, validate=True)
		except Exception:
			return None

	for key in BODY_RAW_FIELDS:
		value = fields.get(key)
		if value:
			return value.encode("utf-8")

	return None


def evaluate_payload_tamper(parsed: dict[str, Any]) -> dict[str, Any]:
	"""Final-stage tamper detection: metadata passes, body hash mismatches trust store."""
	if not parsed.get("valid"):
		return {"checked": False, "reason": "invalid_payload"}

	ecu_id = parsed.get("ecu_id")
	build = parsed.get("build")
	sw = parsed.get("sw")
	modules = parsed.get("modules", [])

	profile = ECU_PROFILES.get(ecu_id)
	if profile is None:
		return {"checked": False, "reason": "unknown_ecu"}

	# Tamper stage runs only after metadata validation prerequisites pass.
	if sw != profile.legit_sw:
		return {"checked": False, "reason": "sw_not_current"}
	if build != profile.legit_build:
		return {"checked": False, "reason": "build_not_recognized"}

	trust_entry = BUILD_CONTENT_TRUST_STORE.get(build)
	if trust_entry is None:
		return {"checked": False, "reason": "build_missing_from_trust_store"}

	expected_modules = trust_entry.get("expected_modules", [])
	if sorted(modules) != sorted(expected_modules):
		return {"checked": False, "reason": "modules_mismatch"}

	body_bytes = extract_raw_payload_body_bytes(parsed)
	if body_bytes is None:
		return {"checked": False, "reason": "raw_body_missing"}

	computed_body_sha256 = hashlib.sha256(body_bytes).hexdigest()
	expected_body_sha256 = trust_entry["expected_body_sha256"]
	tampered = computed_body_sha256 != expected_body_sha256

	return {
		"checked": True,
		"tampered": tampered,
		"build": build,
		"ecu_id": ecu_id,
		"computed_body_sha256": computed_body_sha256,
		"expected_body_sha256": expected_body_sha256,
		"reason": "content_hash_mismatch" if tampered else "content_hash_match",
	}


def classify_payload(payload_text: str) -> dict[str, Any]:
	"""Classify payload into likely scenario using dataset-aligned reasoning."""
	parsed = parse_firmware_payload(payload_text)
	if not parsed.get("valid"):
		return {
			"parsed": parsed,
			"scenario": "invalid_payload",
			"threat_classification": THREAT_LEGITIMATE,
			"confidence": "high",
			"risk": "UNKNOWN",
			"reasoning": [parsed.get("error", "invalid payload")],
			"iocs": [],
			"target_ecu": "maps_ecu",
			"execution_mode": "reject_early",
		}

	ecu_id = parsed["ecu_id"]
	sw = parsed["sw"]
	profile = ECU_PROFILES.get(ecu_id)

	if profile is None:
		return {
			"parsed": parsed,
			"scenario": "unknown_ecu",
			"threat_classification": THREAT_ROGUE_VERSION,
			"confidence": "medium",
			"risk": "HIGH",
			"reasoning": [
				f"ECU_ID {ecu_id} is not in the approved profile list.",
				"Treat as suspicious until explicitly allowlisted.",
			],
			"iocs": ["unknown_ecu_id"],
			"target_ecu": "maps_ecu",
			"execution_mode": "force_rogue_source",
		}

	reasoning: list[str] = []
	iocs: list[str] = []
	confidence = "high"
	scenario = "legitimate_ota"
	execution_mode = "normal"
	delivery_context = DeliveryContext(
		source=LEGITIMATE_SOURCE,
		delivery_channel=WIRELESS_CHANNEL,
		requires_charging_state=False,
	)

	if parsed.get("hw") and parsed["hw"] != profile.hardware_rev:
		iocs.append("hardware_revision_mismatch")
		reasoning.append(
			f"HW {parsed['hw']} differs from baseline {profile.hardware_rev} for {ecu_id}."
		)

	if sw == profile.rogue_sw and sw == "9.9.9":
		scenario = "rogue_charger"
		execution_mode = "force_rogue_source"
		delivery_context = DeliveryContext(
			source=ROGUE_SOURCE,
			delivery_channel=CHARGER_CHANNEL,
			requires_charging_state=True,
		)
		iocs.append("sentinel_sw_9_9_9")
		reasoning.append(
			"SW version jumped to sentinel 9.9.9, a known spoof/injection indicator."
		)
		if parsed.get("build") == profile.legit_build:
			iocs.append("build_hash_clone")
			reasoning.append("BUILD hash matches legitimate release metadata despite rogue version.")

	elif _as_version_tuple(sw) < _as_version_tuple(profile.legit_sw):
		scenario = "rollback_attack"
		execution_mode = "version_guard"
		delivery_context = DeliveryContext(
			source=LEGITIMATE_SOURCE,
			delivery_channel=WIRELESS_CHANNEL,
			requires_charging_state=False,
		)
		iocs.append("version_regression")
		reasoning.append(
			f"Incoming SW {sw} is below deployed baseline {profile.legit_sw}; rollback detected."
		)
		if not parsed.get("patches"):
			iocs.append("patch_strip_pattern")
			reasoning.append("PATCHES field missing/empty in rollback sample, indicating CVE re-exposure risk.")

	elif sw == profile.legit_sw:
		scenario = "legitimate_or_metadata_clone"
		execution_mode = "normal"
		delivery_context = DeliveryContext(
			source=LEGITIMATE_SOURCE,
			delivery_channel=WIRELESS_CHANNEL,
			requires_charging_state=False,
		)
		reasoning.append(
			"SW matches baseline release version. Metadata alone cannot prove authenticity."
		)
		if ecu_id == "CHAS-4.0":
			confidence = "medium"
			iocs.append("stealth_clone_possible")
			reasoning.append(
				"Chassis dataset includes a stealth rogue clone with identical metadata; rely on signature/hash validation."
			)

	else:
		scenario = "version_anomaly"
		execution_mode = "normal"
		confidence = "medium"
		delivery_context = DeliveryContext(
			source=LEGITIMATE_SOURCE,
			delivery_channel=WIRELESS_CHANNEL,
			requires_charging_state=False,
		)
		iocs.append("unexpected_version_pattern")
		reasoning.append(
			f"SW {sw} is neither baseline {profile.legit_sw} nor rollback {profile.rollback_sw}; manual review required."
		)

	if ecu_id == "INFO-1.8" and sw == "9.9.9":
		iocs.append("rollback_label_anomaly")
		reasoning.append(
			"Infotainment dataset marks one rollback sample with SW 9.9.9, indicating double-deception/label anomaly."
		)

	if parsed.get("build") == profile.legit_build and scenario in {"rogue_charger", "legitimate_or_metadata_clone"}:
		reasoning.append("Same BUILD identifier as legitimate release suggests metadata reuse by attacker or insider access.")

	return {
		"parsed": parsed,
		"threat_classification": {
			"legitimate_ota": THREAT_LEGITIMATE,
			"rogue_charger": THREAT_ROGUE_VERSION,
			"rollback_attack": THREAT_ROLLBACK,
			"legitimate_or_metadata_clone": THREAT_LEGITIMATE,
			"version_anomaly": THREAT_ROGUE_VERSION,
		}.get(scenario, THREAT_LEGITIMATE),
		"profile": {
			"ecu_id": profile.ecu_id,
			"legit_sw": profile.legit_sw,
			"rogue_sw": profile.rogue_sw,
			"rollback_sw": profile.rollback_sw,
			"risk": profile.risk,
		},
		"delivery_context": {
			"source": delivery_context.source,
			"delivery_channel": delivery_context.delivery_channel,
			"requires_charging_state": delivery_context.requires_charging_state,
		},
		"scenario": scenario,
		"confidence": confidence,
		"risk": profile.risk,
		"reasoning": reasoning,
		"iocs": iocs,
		"target_ecu": profile.target_ecu,
		"execution_mode": execution_mode,
	}


def evaluate_delivery_gate(vehicle_state: dict[str, Any], classification: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
	"""Evaluate the compound state/source gate before cryptographic verification."""
	parsed = classification.get("parsed", {})
	target_ecu = classification.get("target_ecu") or parsed.get("ecu_id") or "maps_ecu"
	req = policy.get(target_ecu, {})
	delivery_context = classification.get("delivery_context", {})
	source = delivery_context.get("source", LEGITIMATE_SOURCE)
	delivery_channel = delivery_context.get("delivery_channel", WIRELESS_CHANNEL)
	requires_charging_state = bool(delivery_context.get("requires_charging_state", False))

	speed = int(vehicle_state.get("speed_kph", 0) or 0)
	battery = int(vehicle_state.get("battery_soc", 0) or 0)
	charging = bool(vehicle_state.get("charging_active", False))
	data_link_locked = bool(vehicle_state.get("data_link_locked", True))

	state_ok = True
	state_reasons: list[str] = []

	max_speed = int(req.get("max_speed", 150) or 150)
	min_battery = int(req.get("min_battery", 0) or 0)
	charging_ok = bool(req.get("charging_ok", True))

	if speed > max_speed:
		state_ok = False
		state_reasons.append(f"speed {speed} exceeds max {max_speed}")
	if battery < min_battery:
		state_ok = False
		state_reasons.append(f"battery {battery}% below min {min_battery}%")
	if charging and not charging_ok:
		state_ok = False
		state_reasons.append("charging state not permitted for this ECU")
	if not data_link_locked:
		state_ok = False
		state_reasons.append("data link is unlocked")

	source_ok = source in {LEGITIMATE_SOURCE, ROGUE_SOURCE}
	source_matches_state = True
	source_reason = ""
	if delivery_channel == CHARGER_CHANNEL:
		source_matches_state = charging
		if not charging:
			source_reason = "charger interface is only valid while charging"
		elif source != ROGUE_SOURCE:
			source_ok = False
			source_reason = "charger delivery must be associated with charging_network source"
	elif delivery_channel == WIRELESS_CHANNEL:
		source_matches_state = True
		if source != LEGITIMATE_SOURCE:
			source_ok = False
			source_reason = "wireless delivery must be sourced from legitimate_ota_server"
	else:
		source_ok = False
		source_matches_state = False
		source_reason = f"unknown delivery channel: {delivery_channel}"

	if requires_charging_state and not charging:
		source_matches_state = False
		if not source_reason:
			source_reason = "scenario requires charging state"

	ok = state_ok and source_ok and source_matches_state
	reasons = []
	if not state_ok:
		reasons.append("state gate failed: " + "; ".join(state_reasons))
	if not source_ok:
		reasons.append("source gate failed: " + (source_reason or f"source {source} not allowed"))
	if state_ok and source_ok and not source_matches_state:
		reasons.append(source_reason or "source does not match current vehicle state")

	return {
		"ok": ok,
		"failed_at": None if ok else "delivery_gate",
		"reason": "Compound delivery gate passed" if ok else "; ".join(reasons) or "delivery gate rejected the payload",
		"state_ok": state_ok,
		"source_ok": source_ok,
		"source_matches_state": source_matches_state,
		"source": source,
		"delivery_channel": delivery_channel,
		"target_ecu": target_ecu,
		"vehicle_state": {
			"speed_kph": speed,
			"battery_soc": battery,
			"charging_active": charging,
			"data_link_locked": data_link_locked,
		},
		"policy": {
			"max_speed": max_speed,
			"min_battery": min_battery,
			"charging_ok": charging_ok,
		},
	}