import pytest
from jose import JWTError

from src.auth.security import decode_jwt, hash_password, issue_jwt, verify_password


def test_hash_verify_roundtrip():
    plain = "supersecret"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip():
    token, expires_in = issue_jwt("42")
    payload = decode_jwt(token)
    assert payload["sub"] == "42"
    assert expires_in > 0


def test_tampered_jwt_rejected():
    token, _ = issue_jwt("42")
    tampered = token[:-4] + "xxxx"
    with pytest.raises(JWTError):
        decode_jwt(tampered)
