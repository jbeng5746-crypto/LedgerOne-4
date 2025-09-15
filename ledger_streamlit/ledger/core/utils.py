
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import json
import time
import hmac
import hashlib
import secrets
from typing import Any, Dict

try:
    from ledger.core.config import settings
except Exception:
    class _S:
        APP_NAME = "LedgerStreamlit"
        AUDIT_LOG_PATH = "./data/logs"
        LOG_LEVEL = "INFO"
    settings = _S()

def mkdir_safe(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)

def atomic_write_json(path: str, obj: Any):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
    os.replace(str(tmp), str(p))

def setup_logging(tenant_id: str = "system", *, log_level: str = None):
    logger_name = f"{settings.APP_NAME}.{tenant_id}"
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger
    level = log_level or getattr(settings, "LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, level))
    audit_dir = getattr(settings, "AUDIT_LOG_PATH", "./data/logs")
    mkdir_safe(audit_dir)
    logfile = Path(audit_dir) / f"{tenant_id}.log"
    handler = RotatingFileHandler(str(logfile), maxBytes=10_000_000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if os.getenv("DEV", "").lower() in ("1","true","yes"):
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    logger.propagate = False
    return logger

def audit_log(tenant_id: str, actor: str, action: str, obj_type: str, obj_id: str, diff: Dict = None):
    audit_dir = getattr(settings, "AUDIT_LOG_PATH", "./data/logs")
    mkdir_safe(audit_dir)
    path = Path(audit_dir) / f"{tenant_id}_audit.jsonl"
    entry = {
        "ts": int(time.time()),
        "actor": actor,
        "action": action,
        "object_type": obj_type,
        "object_id": obj_id,
        "diff": diff or {}
    }
    with open(path.with_suffix(".tmp"), "w", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return True

def hash_password(password: str, *, salt: bytes = None, iterations: int = 180000) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations_s, salt_hex, hash_hex = stored.split("$")
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False
