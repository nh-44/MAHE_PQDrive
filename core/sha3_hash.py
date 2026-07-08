import hashlib
import json


def serialize_package(package: dict) -> bytes:
    """
    Serialize a package dict to bytes for hashing.
    Uses JSON with sorted keys for deterministic output.
    """
    return json.dumps(package, sort_keys=True, default=str).encode("utf-8")


def hash_package(data: bytes) -> str:
    """
    Hash firmware payload bytes using SHA3-256.
    Returns hex string of the hash.
    """
    return hashlib.sha3_256(data).hexdigest()


def verify_hash(data: bytes, expected_hex: str) -> bool:
    """
    Verify that the hash of data matches the expected hex string.
    Returns True if intact, False if tampered.
    """
    return hash_package(data) == expected_hex