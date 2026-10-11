"""Password hashing: stdlib scrypt behind a version prefix (ADR-0003). Call outside any write transaction."""
from __future__ import annotations

import hashlib
import hmac
import os
from functools import lru_cache

PREFIX = "scrypt1"  # scrypt1$<salt hex>$<hash hex>; parameters belong to the version
N, R, P, DKLEN = 2**14, 8, 1, 32


def _kdf(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8", "surrogatepass"), salt=salt, n=N, r=R, p=P,
                          maxmem=64 * 1024 * 1024, dklen=DKLEN)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    return f"{PREFIX}${salt.hex()}${_kdf(password, salt).hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        prefix, salt_hex, hash_hex = stored.split("$")
        if prefix != PREFIX:
            return False
        expected = bytes.fromhex(hash_hex)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    return hmac.compare_digest(_kdf(password, salt), expected)


@lru_cache(maxsize=1)
def dummy_hash() -> str:
    """Verified against when the email is unknown, so timing does not reveal which accounts exist."""
    return hash_password("not-a-real-password")
