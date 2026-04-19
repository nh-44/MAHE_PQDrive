"""Enhanced OTA verification pipeline with detailed chain-of-thought logging."""

from __future__ import annotations

from time import perf_counter

from . import dilithium, kyber, sha3_hash, version_check
from .scenario_logger import ScenarioLogger


class OTAVerificationPipelineWithLogging:
	"""Run all mandatory checks with detailed logging for transparency."""

	def __init__(
		self,
		vehicle_public_key: bytes,
		vehicle_private_key: bytes,
		server_public_key: bytes,
		enable_logging: bool = True,
	) -> None:
		self.vehicle_public_key = vehicle_public_key
		self.vehicle_private_key = vehicle_private_key
		self.server_public_key = server_public_key
		self.enable_logging = enable_logging
		self.logger: ScenarioLogger | None = None

	def run(self, update_package: dict) -> dict:
		"""Execute OTA verification with detailed logging."""
		if self.enable_logging:
			self.logger = ScenarioLogger("OTA_Update_Verification")

		result = {
			"kyber_ok": False,
			"dilithium_ok": False,
			"hash_ok": False,
			"version_ok": False,
			"all_passed": False,
			"failed_at": None,
			"verification_trace": [],
			"stage_durations_ms": {},
			"decision_chain": [],
			"scenario_logs": None,
		}

		# ===== KYBER SESSION VERIFICATION =====
		if self.logger:
			self.logger.log_condition("Incoming Version", update_package.get("incoming_version", "unknown"))
			self.logger.log_condition("Current Version", update_package.get("current_version", "unknown"))

		stage_started = perf_counter()
		result["kyber_ok"] = kyber.verify_session(
			self.vehicle_private_key,
			update_package["ciphertext"],
			update_package["session_key"],
		)
		duration = round((perf_counter() - stage_started) * 1000, 3)
		result["stage_durations_ms"]["kyber"] = duration
		result["verification_trace"].append({
			"stage": "kyber",
			"ok": result["kyber_ok"],
			"duration_ms": duration
		})

		if self.logger:
			self.logger.log_crypto_operation("Kyber Session Verification", duration, result["kyber_ok"])
			self.logger.log_check("Kyber KEM", result["kyber_ok"], "Session key encapsulation OK" if result["kyber_ok"] else "Session key mismatch")

		if not result["kyber_ok"]:
			result["failed_at"] = "kyber"
			if self.logger:
				self.logger.log_defense("KEM Defense", "Invalid session - rejected")
				self.logger.log_decision(f"{update_package.get('incoming_version')} → {update_package.get('current_version')}", False)
				self.logger.finalize()
				result["scenario_logs"] = self.logger.get_chain_of_thought()
			return result

		# ===== DILITHIUM SIGNATURE VERIFICATION =====
		stage_started = perf_counter()
		result["dilithium_ok"] = dilithium.verify(
			self.server_public_key,
			update_package["payload"],
			update_package["signature"],
		)
		duration = round((perf_counter() - stage_started) * 1000, 3)
		result["stage_durations_ms"]["dilithium"] = duration
		result["verification_trace"].append({
			"stage": "dilithium",
			"ok": result["dilithium_ok"],
			"duration_ms": duration
		})

		if self.logger:
			self.logger.log_crypto_operation("Dilithium Signature Verification", duration, result["dilithium_ok"])
			self.logger.log_check("Dilithium SIG", result["dilithium_ok"], "Server signature valid" if result["dilithium_ok"] else "Invalid signature")

		if not result["dilithium_ok"]:
			result["failed_at"] = "dilithium"
			if self.logger:
				self.logger.log_defense("Signature Defense", "Forged/tampered package - rejected")
				self.logger.log_decision(f"{update_package.get('incoming_version')} → {update_package.get('current_version')}", False)
				self.logger.finalize()
				result["scenario_logs"] = self.logger.get_chain_of_thought()
			return result

		# ===== SHA3-256 INTEGRITY CHECK =====
		stage_started = perf_counter()
		result["hash_ok"] = sha3_hash.verify_hash(
			update_package["payload"],
			update_package["package_hash"],
		)
		duration = round((perf_counter() - stage_started) * 1000, 3)
		result["stage_durations_ms"]["hash"] = duration
		result["verification_trace"].append({
			"stage": "hash",
			"ok": result["hash_ok"],
			"duration_ms": duration
		})

		if self.logger:
			self.logger.log_crypto_operation("SHA3-256 Integrity Check", duration, result["hash_ok"])
			self.logger.log_check("Integrity", result["hash_ok"], "Payload unchanged" if result["hash_ok"] else "Payload corrupted")

		if not result["hash_ok"]:
			result["failed_at"] = "hash"
			if self.logger:
				self.logger.log_defense("Integrity Defense", "Corrupted payload - rejected")
				self.logger.log_decision(f"{update_package.get('incoming_version')} → {update_package.get('current_version')}", False)
				self.logger.finalize()
				result["scenario_logs"] = self.logger.get_chain_of_thought()
			return result

		# ===== VERSION CHECK =====
		stage_started = perf_counter()
		result["version_ok"] = version_check.is_valid_version(
			update_package["current_version"],
			update_package["incoming_version"],
		)
		duration = round((perf_counter() - stage_started) * 1000, 3)
		result["stage_durations_ms"]["version"] = duration
		result["verification_trace"].append({
			"stage": "version",
			"ok": result["version_ok"],
			"duration_ms": duration
		})

		if self.logger:
			self.logger.log_crypto_operation("Version Check", duration, result["version_ok"])
			self.logger.log_check(
				"Version Policy",
				result["version_ok"],
				f"Valid upgrade: {update_package['current_version']} → {update_package['incoming_version']}" if result["version_ok"] else "Downgrade or lateral move blocked"
			)

		if not result["version_ok"]:
			result["failed_at"] = "version"
			if self.logger:
				self.logger.log_defense("Version Defense", "Downgrade attack - rejected")
				self.logger.log_decision(f"{update_package.get('incoming_version')} → {update_package.get('current_version')}", False)
				self.logger.finalize()
				result["scenario_logs"] = self.logger.get_chain_of_thought()
			return result

		# ===== ALL CHECKS PASSED =====
		result["all_passed"] = True
		result["veracity_score"] = 1.0

		if self.logger:
			self.logger.log_state_transition("VERIFICATION_IN_PROGRESS", "VERIFICATION_COMPLETE")
			self.logger.log_decision(f"{update_package.get('incoming_version')} → {update_package.get('current_version')}", True)
			self.logger.finalize()
			result["scenario_logs"] = self.logger.get_chain_of_thought()

		return result
