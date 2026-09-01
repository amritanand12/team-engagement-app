"""
Authentication & Password Security Service.
Implements NIST-compliant PBKDF2-HMAC-SHA256 password hashing with per-user salts
and cryptographically signed HMAC-SHA256 session tokens (zero external C-dependencies).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.config import get_settings

settings = get_settings()
SECRET_KEY = settings.ADMIN_API_KEY.encode("utf-8")
TOKEN_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days


def hash_password(password: str) -> str:
    """Hashes password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a 16-byte random salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2:sha256:100000${salt}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a plain password against the stored hash in constant time."""
    try:
        parts = password_hash.split("$")
        if len(parts) != 3:
            return False
        meta, salt, stored_hash = parts
        _, algo, iterations = meta.split(":")
        dk = hashlib.pbkdf2_hmac(algo, password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
        return hmac.compare_digest(dk.hex(), stored_hash)
    except Exception:
        return False


def _b64encode_str(data: str) -> str:
    return base64.urlsafe_b64encode(data.encode("utf-8")).decode("utf-8").rstrip("=")


def _b64decode_str(data: str) -> str:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding).decode("utf-8")


def create_access_token(payload: dict[str, Any], expires_in: int = TOKEN_EXPIRY_SECONDS) -> str:
    """Generates an HMAC-SHA256 signed access token with an expiration timestamp."""
    payload_copy = payload.copy()
    payload_copy["exp"] = int(time.time()) + expires_in
    payload_copy["iat"] = int(time.time())

    header = {"alg": "HS256", "typ": "JWT"}
    h_b64 = _b64encode_str(json.dumps(header, separators=(",", ":")))
    p_b64 = _b64encode_str(json.dumps(payload_copy, separators=(",", ":")))

    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
    sig = hmac.new(SECRET_KEY, signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

    return f"{h_b64}.{p_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Validates signature and expiration of an access token, returning the payload if valid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h_b64, p_b64, sig_b64 = parts

        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY, signing_input, hashlib.sha256).digest()
        actual_sig = base64.urlsafe_b64decode(sig_b64 + "=" * ((4 - len(sig_b64) % 4) % 4))

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64decode_str(p_b64))
        if payload.get("exp", 0) < int(time.time()):
            return None  # Expired

        return payload
    except Exception:
        return None
