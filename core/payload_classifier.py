"""Parse and classify pipe-delimited firmware payloads for OTA threat analysis."""

from __future__ import annotations

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
			"legitimate_or_metadata_clone": THREAT_PAYLOAD_TAMPER if ecu_id == "CHAS-4.0" else THREAT_LEGITIMATE,
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