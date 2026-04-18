"""ECU domain and deployment-policy management for OTA rollout control."""

from __future__ import annotations

from pathlib import Path

import yaml


INFOTAINMENT = "infotainment"
SAFETY_CRITICAL = "safety_critical"


class ECUDomainManager:
	"""Loads ECU policies and answers deployment control questions."""

	def __init__(self, policy_path: str = "config/ecu_policy.yaml") -> None:
		policy_file = Path(policy_path)
		if not policy_file.is_absolute():
			policy_file = Path(__file__).resolve().parents[1] / policy_path

		with policy_file.open("r", encoding="utf-8") as f:
			self.policy = yaml.safe_load(f) or {}

		self.ecus = self.policy.get("ecus", {})
		self.charging_policy = self.policy.get("charging_policy", {})

	def get_domain(self, ecu_name: str) -> str:
		"""Return the configured ECU domain, defaulting to infotainment."""
		return self.ecus.get(ecu_name, {}).get("domain", INFOTAINMENT)

	def can_auto_deploy(self, ecu_name: str) -> bool:
		"""Return True for infotainment ECU auto-deploy policy."""
		return bool(self.ecus.get(ecu_name, {}).get("auto_deploy", False))

	def requires_dual_auth(self, ecu_name: str) -> bool:
		"""Return True for safety-critical ECU dual-authorization policy."""
		return bool(self.ecus.get(ecu_name, {}).get("requires_dual_auth", False))

	def requires_authenticated_charger(self, ecu_name: str) -> bool:
		"""Return True when a charger-mediated update needs a verified charger."""
		return self.get_domain(ecu_name) == SAFETY_CRITICAL

	def allow_updates_while_charging(self, ecu_name: str) -> bool:
		"""Return True when charging-state updates are allowed for the ECU."""
		if self.get_domain(ecu_name) == SAFETY_CRITICAL:
			return bool(self.charging_policy.get("allow_safety_critical_updates_while_charging", False))
		return bool(self.charging_policy.get("allow_infotainment_updates_while_charging", True))
