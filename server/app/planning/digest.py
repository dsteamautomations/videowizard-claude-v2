"""Canonical JSON digest shared by the planning modules (same formatting as v1 store.digest)."""
import hashlib, json


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
