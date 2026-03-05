import hashlib


def create_lock_key(name: str) -> int:
    """
    Create advisory lock value using deterministic hash functions to guarantee
    value is the same across multiple processes:
    Use SHA‑256 and take first 8 bytes (64 bits), then ensure it's within signed bigint range
    """
    hash_bytes = hashlib.sha256(name.encode()).digest()[:8]
    return int.from_bytes(hash_bytes, "big") & 0x7FFFFFFFFFFFFFFF
