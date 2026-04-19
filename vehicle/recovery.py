"""Recovery and forensic audit helpers for OTA failures and incidents."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core import dilithium


class RecoveryManager:
	"""Maintains snapshots and signed audit events for rollback workflows.
	
	SECURITY FIX (Phase 7E): Persist audit logs to disk and use persistent keys.
	"""

	def __init__(self) -> None:
		self.snapshots: dict[str, dict] = {}
		self.audit_log: list[dict] = []
		
		# SECURITY FIX: Use persistent files for logs and keys
		self.log_file = Path("audit_logs.jsonl")
		self.key_file = Path("audit_keys.json")
		
		# Load or create persistent audit keys
		self._audit_public_key, self._audit_private_key = self._load_or_create_keys()
		
		# Load existing audit log from disk
		self.audit_log = self._load_audit_log()

	def _load_or_create_keys(self) -> tuple[bytes, bytes]:
		"""Load persistent audit keys from disk or create and save if missing."""
		if self.key_file.exists():
			try:
				with open(self.key_file, "r") as f:
					key_data = json.load(f)
					return (
						bytes.fromhex(key_data["public"]),
						bytes.fromhex(key_data["private"])
					)
			except Exception as e:
				print(f"Warning: Failed to load keys from {self.key_file}: {e}")
		
		# Create new keys and persist
		pub, priv = dilithium.generate_keypair()
		try:
			with open(self.key_file, "w") as f:
				json.dump({
					"public": pub.hex(),
					"private": priv.hex(),
					"created": datetime.now(timezone.utc).isoformat(),
				}, f)
		except Exception as e:
			print(f"Warning: Failed to save keys to {self.key_file}: {e}")
		
		return pub, priv
	
	def _load_audit_log(self) -> list[dict]:
		"""Load existing JSONL audit log from disk."""
		if not self.log_file.exists():
			return []
		
		log = []
		try:
			with open(self.log_file, "r") as f:
				for line in f:
					try:
						entry = json.loads(line)
						log.append(entry)
					except json.JSONDecodeError:
						pass
		except Exception as e:
			print(f"Warning: Failed to load audit log: {e}")
		
		return log

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
		self._persist_audit_entry(entry)
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
		"""Append a Dilithium-signed audit event for non-repudiation.
		
		SECURITY FIX: Persist to disk as JSONL.
		"""
		entry = {
			"event_type": event_type,
			"details": details,
			"timestamp": datetime.now(timezone.utc).isoformat(),
		}
		serialized = json.dumps(entry, sort_keys=True).encode("utf-8")
		signature = dilithium.sign(self._audit_private_key, serialized)
		entry["signature"] = signature.hex()
		self.audit_log.append(entry)
		
		# SECURITY FIX: Persist to disk immediately
		self._persist_audit_entry(entry)
	
	def _persist_audit_entry(self, entry: dict) -> None:
		"""Write an audit entry to persistent JSONL log."""
		try:
			with open(self.log_file, "a") as f:
				json.dump(entry, f)
				f.write("\n")
		except Exception as e:
			print(f"Warning: Failed to persist audit entry: {e}")

	def get_audit_log(self) -> list:
		"""Return all recorded audit entries."""
		return self.audit_log
