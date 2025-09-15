from pydantic import BaseSettings, Field
from typing import List, Tuple

class Settings(BaseSettings):
    SECRET_KEY: str = Field("change-me", description="Secret for dev. Override in prod via env.")
    SUPERADMIN_EMAIL: str = Field("dev@you.com", description="Developer superadmin email")
    DB_URL: str = Field("sqlite:///./data/ledger.db", description="Database URL")

    # Statutory defaults (Kenya, 2023)
    # NSSF (new rates as of Feb 2023)
    NSSF_EMPLOYEE_RATE: float = 0.06
    NSSF_EMPLOYER_RATE: float = 0.06
    NSSF_TIER_1_UPPER: float = 6000.0
    NSSF_TIER_2_UPPER: float = 18000.0

    # NHIF/SHA (Standard Health Authority) - approximated
    SHA_RATES: List[Tuple[float,float]] = [
        (5999, 150),
        (7999, 300),
        (11999, 400),
        (14999, 500),
        (19999, 600),
        (24999, 750),
        (29999, 850),
        (34999, 900),
        (39999, 950),
        (44999, 1000),
        (49999, 1100),
        (59999, 1200),
        (69999, 1300),
        (79999, 1400),
        (89999, 1500),
        (99999, 1600),
        (float("inf"), 1700),
    ]

    # PAYE (Kenya Finance Act 2023)
    PAYE_BANDS: List[Tuple[float,float]] = [
        (24000, 0.10),
        (32333, 0.25),
        (500000, 0.30),
        (800000, 0.325),
        (float("inf"), 0.35),
    ]
    PERSONAL_RELIEF_MONTHLY: float = 2400.0

settings = Settings()
