"""SHA3 integrity helpers for OTA update payloads."""

from __future__ import annotations

import hashlib
import json


def serialize_package(package: dict) -> bytes:
	"""Serialize a package dictionary into deterministic JSON bytes."""
	return json.dumps(package, sort_keys=True, default=str).encode("utf-8")


def hash_package(data: bytes) -> str:
	"""Compute SHA3-256 hex digest for firmware payload bytes."""
	return hashlib.sha3_256(data).hexdigest()


def verify_hash(data: bytes, expected_hex: str) -> bool:
	"""Check whether payload bytes match an expected SHA3-256 digest."""
	return hash_package(data) == expected_hex
