def get_version_tuple(version_str: str) -> tuple:
    """
    Convert a semantic version string to a tuple of ints.
    e.g. "1.2.3" → (1, 2, 3)
    """
    try:
        return tuple(int(x) for x in version_str.strip().split("."))
    except ValueError:
        raise ValueError(f"Invalid version format: '{version_str}' — expected format like '1.2.3'")


def is_valid_version(current_version: str, incoming_version: str) -> bool:
    """
    Returns True only if incoming_version is strictly greater than current_version.
    Equal or lower versions are rejected to prevent rollback attacks.
    """
    current = get_version_tuple(current_version)
    incoming = get_version_tuple(incoming_version)
    return incoming > current