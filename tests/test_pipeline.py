from __future__ import annotations

from core import dilithium, kyber, sha3_hash, version_check
from core.pipeline import OTAVerificationPipeline
from vehicle.ota_server import OTAServer


def test_kyber_keygen_and_session() -> None:
	public_key, private_key = kyber.generate_keypair()
	ciphertext, encapsulated_key = kyber.encapsulate(public_key)
	decapsulated_key = kyber.decapsulate(private_key, ciphertext)
	assert decapsulated_key == encapsulated_key


def test_dilithium_sign_verify() -> None:
	public_key, private_key = dilithium.generate_keypair()
	message = b"test message"
	signature = dilithium.sign(private_key, message)
	assert dilithium.verify(public_key, message, signature) is True


def test_dilithium_bad_signature() -> None:
	public_key_a, private_key_a = dilithium.generate_keypair()
	public_key_b, _ = dilithium.generate_keypair()
	message = b"test message"
	signature = dilithium.sign(private_key_a, message)
	assert dilithium.verify(public_key_b, message, signature) is False
	assert dilithium.verify(public_key_a, b"wrong message", signature) is False


def test_sha3_hash() -> None:
	payload = b"firmware_payload"
	digest = sha3_hash.hash_package(payload)
	assert sha3_hash.verify_hash(payload, digest) is True
	assert sha3_hash.verify_hash(payload + b"_mutated", digest) is False


def test_version_check_valid() -> None:
	assert version_check.is_valid_version("1.0.0", "2.0.0") is True


def test_version_check_rollback() -> None:
	assert version_check.is_valid_version("2.0.0", "1.0.0") is False


def test_version_check_same() -> None:
	assert version_check.is_valid_version("1.0.0", "1.0.0") is False


def test_full_pipeline_pass() -> None:
	vehicle_public_key, vehicle_private_key = kyber.generate_keypair()
	server_public_key, server_private_key = dilithium.generate_keypair()

	server = OTAServer(
		server_private_key=server_private_key,
		server_public_key=server_public_key,
		vehicle_public_key=vehicle_public_key,
	)
	pipeline = OTAVerificationPipeline(
		vehicle_public_key=vehicle_public_key,
		vehicle_private_key=vehicle_private_key,
		server_public_key=server_public_key,
	)

	package = server.prepare_update(
		payload=b"firmware_v2",
		current_version="1.0.0",
		new_version="2.0.0",
	)
	result = pipeline.run(package)

	assert result["kyber_ok"] is True
	assert result["dilithium_ok"] is True
	assert result["hash_ok"] is True
	assert result["version_ok"] is True
	assert result["all_passed"] is True
	assert result["failed_at"] is None


def test_pipeline_fails_on_tamper() -> None:
	vehicle_public_key, vehicle_private_key = kyber.generate_keypair()
	server_public_key, server_private_key = dilithium.generate_keypair()

	server = OTAServer(
		server_private_key=server_private_key,
		server_public_key=server_public_key,
		vehicle_public_key=vehicle_public_key,
	)
	pipeline = OTAVerificationPipeline(
		vehicle_public_key=vehicle_public_key,
		vehicle_private_key=vehicle_private_key,
		server_public_key=server_public_key,
	)

	package = server.prepare_update(
		payload=b"firmware_v2",
		current_version="1.0.0",
		new_version="2.0.0",
	)

	# Payload is hex-encoded in transport; corrupt hash to simulate integrity tamper
	package["package_hash"] = ("0" if package["package_hash"][0] != "0" else "1") + package["package_hash"][1:]

	result = pipeline.run(package)
	assert result["hash_ok"] is False
	assert result["all_passed"] is False
