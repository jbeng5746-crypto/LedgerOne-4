
import logging
from ledger.core.utils import setup_logging, hash_password, verify_password

def test_setup_logging_idempotent(tmp_path):
    tenant = "tmptest"
    logger1 = setup_logging(tenant)
    handlers_before = len(logger1.handlers)
    logger2 = setup_logging(tenant)
    handlers_after = len(logger2.handlers)
    assert handlers_before == handlers_after
    assert any(isinstance(h, logging.handlers.RotatingFileHandler) for h in logger2.handlers)

def test_password_hash_and_verify():
    pw = "S3cureP@ssw0rd!"
    stored = hash_password(pw)
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password(pw, stored) is True
    assert verify_password("wrongpass", stored) is False
