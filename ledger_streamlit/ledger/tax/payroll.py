
from typing import Dict

# PAYE Bands (Kenya 2025 monthly, KES)
PAYE_BANDS = [
    (24000, 0.10),
    (32333, 0.25),
    (500000, 0.30),
    (800000, 0.325),
    (float("inf"), 0.35),
]

# NSSF: 6% employee + 6% employer, Tier I capped at 7,000, Tier II capped at 29,000
NSSF_TIER1_LIMIT = 7000
NSSF_TIER2_LIMIT = 29000
NSSF_RATE = 0.06

# NHIF: 2025 bands (simplified for demo)
NHIF_BANDS = [
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

VAT_RATE = 0.16

class KenyanPayroll:
    def compute_paye(self, gross: float) -> float:
        tax=0; remaining=gross
        prev_limit=0
        for limit,rate in PAYE_BANDS:
            band=min(remaining,limit-prev_limit)
            if band<=0: break
            tax+=band*rate
            remaining-=band
            prev_limit=limit
        return round(tax,2)

    def compute_nssf(self, gross: float) -> float:
        tier1=min(gross,NSSF_TIER1_LIMIT)*NSSF_RATE
        tier2=0
        if gross>NSSF_TIER1_LIMIT:
            tier2=min(gross-NSSF_TIER1_LIMIT,NSSF_TIER2_LIMIT-NSSF_TIER1_LIMIT)*NSSF_RATE
        return round(tier1+tier2,2)

    def compute_nhif(self, gross: float) -> float:
        for limit,contrib in NHIF_BANDS:
            if gross<=limit: return contrib
        return NHIF_BANDS[-1][1]

    def payroll_breakdown(self, gross: float) -> Dict[str,float]:
        paye=self.compute_paye(gross)
        nssf=self.compute_nssf(gross)
        nhif=self.compute_nhif(gross)
        deductions=paye+nssf+nhif
        net=gross-deductions
        return {"Gross":gross,"PAYE":paye,"NSSF":nssf,"NHIF":nhif,"Net":net}

class KenyanVAT:
    def compute_vat(self, amount: float, rate: float=VAT_RATE) -> float:
        return round(amount*rate,2)
