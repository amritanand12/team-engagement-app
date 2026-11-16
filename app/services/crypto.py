from __future__ import annotations

import base64
import hashlib
import hmac
import os

from app.config import get_settings
settings = get_settings()


def _derive_keys(secret: str) -> tuple[bytes, bytes]:
    enc_key = hashlib.sha256((secret + ':enc').encode('utf-8')).digest()
    mac_key = hashlib.sha256((secret + ':mac').encode('utf-8')).digest()
    return enc_key, mac_key



def encrypt_credential(plaintext: str | None = None) -> str | None:
    if not plaintext:
        return plaintext
    enc_key, mac_key = _derive_keys(settings.SECRET_KEY)
    nonce = os.urandom(16)
    plaintext_bytes = plaintext.encode('utf-8')
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(plaintext_bytes):
        block = hmac.new(enc_key, nonce + counter.to_bytes(4, 'big'), hashlib.sha256).digest()
        keystream.extend(block)
        counter += 1
    ciphertext = bytes(p ^ k for p, k in zip(plaintext_bytes, keystream[:len(plaintext_bytes)]))
    tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()[:16]
    payload = nonce + tag + ciphertext
    return "enc:v1:" + base64.urlsafe_b64encode(payload).decode('ascii')



def decrypt_credential(encoded: str | None = None) -> str | None:
    if not encoded:
        return encoded
    if encoded.startswith("enc:v1:"):
        encoded = encoded[7:]
    try:
        raw = base64.urlsafe_b64decode(encoded.encode('ascii'))
        if len(raw) < 32:
            return encoded
        nonce = raw[:16]
        tag = raw[16:32]
        ciphertext = raw[32:]
        enc_key, mac_key = _derive_keys(settings.SECRET_KEY)
        expected_tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected_tag):
            return encoded
        keystream = bytearray()
        counter = 0
        while len(keystream) < len(ciphertext):
            block = hmac.new(enc_key, nonce + counter.to_bytes(4, 'big'), hashlib.sha256).digest()
            keystream.extend(block)
            counter += 1
        plaintext_bytes = bytes(_c ^ _g for _c, _g in zip(ciphertext, keystream[:len(ciphertext)]))
        return plaintext_bytes.decode('utf-8')
    except Exception:
        return encoded
