"""Version checking utilities to block rollback OTA attacks."""

from __future__ import annotations


def get_version_tuple(version_str: str) -> tuple[int, ...]:
	"""Convert a semantic version string (e.g. 1.2.3) to an int tuple."""
	return tuple(int(part) for part in version_str.strip().split("."))


def is_valid_version(current_version: str, incoming_version: str) -> bool:
	"""Return True only when incoming version is strictly newer than current."""
	current_tuple = get_version_tuple(current_version)
	incoming_tuple = get_version_tuple(incoming_version)
	return incoming_tuple > current_tuple
