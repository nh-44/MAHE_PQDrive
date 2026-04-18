"""Recovery and forensic audit helpers for OTA failures and incidents."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from core import dilithium


class RecoveryManager:
	"""Maintains snapshots and signed audit events for rollback workflows."""

	def __init__(self) -> None:
		self.snapshots: dict[str, dict] = {}
		self.audit_log: list[dict] = []
		self._audit_public_key, self._audit_private_key = dilithium.generate_keypair()

	def take_snapshot(self, ecu_name: str, firmware_version: str, state: dict) -> None:
		"""Store the latest ECU snapshot before applying an update."""
		self.snapshots[ecu_name] = {
			"ecu_name": ecu_name,
			"firmware_version": firmware_version,
			"state": state,
			"timestamp": datetime.now(timezone.utc).isoformat(),
		}

	def isolate_ecu(self, ecu_name: str) -> dict:
		"""Record ECU isolation action to contain potential compromise."""
		entry = {
			"event": "isolate_ecu",
			"ecu_name": ecu_name,
			"message": f"{ecu_name} isolated from CAN bus",
			"timestamp": datetime.now(timezone.utc).isoformat(),
		}
		self.audit_log.append(entry)
		return entry

	def rollback(self, ecu_name: str) -> dict:
		"""Rollback ECU to its latest snapshot if one exists."""
		snapshot = self.snapshots.get(ecu_name)
		if snapshot is None:
			return {
				"success": False,
				"ecu_name": ecu_name,
				"reason": "no snapshot available",
			}

		return {
			"success": True,
			"ecu_name": ecu_name,
			"restored_version": snapshot["firmware_version"],
			"state": snapshot["state"],
			"timestamp": datetime.now(timezone.utc).isoformat(),
		}

	def log_event(self, event_type: str, details: dict) -> None:
		"""Append a Dilithium-signed audit event for non-repudiation."""
		entry = {
			"event_type": event_type,
			"details": details,
			"timestamp": datetime.now(timezone.utc).isoformat(),
		}
		serialized = json.dumps(entry, sort_keys=True).encode("utf-8")
		signature = dilithium.sign(self._audit_private_key, serialized)
		entry["signature"] = signature.hex()
		self.audit_log.append(entry)

	def get_audit_log(self) -> list:
		"""Return all recorded audit entries."""
		return self.audit_log
