import pytest
from fastapi import HTTPException, status
from app.services.security.secure_password import Hasher


def test_verify_password_correct():
    plain_password = "mysecretpassword"
    hashed_password = Hasher.get_password_hash(plain_password)
    assert Hasher.verify_password(plain_password, hashed_password) == True

def test_verify_password_incorrect():
    plain_password = "mysecretpassword"
    wrong_password = "wrongpassword"
    hashed_password = Hasher.get_password_hash(plain_password)
    assert Hasher.verify_password(wrong_password, hashed_password) == False

def test_verify_password_invalid_hash():
    plain_password = "mysecretpassword"
    invalid_hash = "invalidhash"
    with pytest.raises(HTTPException) as exc_info:
        Hasher.verify_password(plain_password, invalid_hash)
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc_info.value.detail == "Password verification failed"


def test_get_password_hash_success():
    password = "mysecretpassword"
    hashed_password = Hasher.get_password_hash(password)
    assert isinstance(hashed_password, str)
    assert len(hashed_password) > 0

def test_get_password_hash_failure():
    pass

def test_get_password_hash_unique():
    password = "mysecretpassword"
    hashed_password1 = Hasher.get_password_hash(password)
    hashed_password2 = Hasher.get_password_hash(password)
    assert hashed_password1 != hashed_password2
