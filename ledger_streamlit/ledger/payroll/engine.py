
from typing import List, Dict
from ledger.core.config import settings

class PayrollEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def compute_paye(self, gross: float) -> float:
        taxable = gross
        tax = 0.0
        prev_band = 0.0
        for band, rate in settings.PAYE_BANDS:
            if taxable > band:
                tax += (band - prev_band) * rate
                prev_band = band
            else:
                tax += (taxable - prev_band) * rate
                break
        tax -= settings.PERSONAL_RELIEF_MONTHLY
        return max(0.0, tax)

    def compute_nssf(self, gross: float) -> float:
        # employee contribution capped
        tier1 = min(gross, settings.NSSF_TIER_1_UPPER) * settings.NSSF_EMPLOYEE_RATE
        if gross > settings.NSSF_TIER_1_UPPER:
            tier2_base = min(gross, settings.NSSF_TIER_2_UPPER) - settings.NSSF_TIER_1_UPPER
            tier2 = tier2_base * settings.NSSF_EMPLOYEE_RATE
        else:
            tier2 = 0.0
        return tier1 + tier2

    def compute_nhif(self, gross: float) -> float:
        for upper, amt in settings.SHA_RATES:
            if gross <= upper:
                return amt
        return settings.SHA_RATES[-1][1]

    def compute_net_pay(self, gross: float) -> Dict[str,float]:
        paye = self.compute_paye(gross)
        nssf = self.compute_nssf(gross)
        nhif = self.compute_nhif(gross)
        deductions = paye + nssf + nhif
        net = gross - deductions
        return {
            "gross": gross,
            "paye": round(paye,2),
            "nssf": round(nssf,2),
            "nhif": round(nhif,2),
            "net": round(net,2)
        }

    def run_payroll(self, employees: List[Dict]) -> List[Dict]:
        results = []
        for e in employees:
            gross = e.get("salary",0.0)
            slip = self.compute_net_pay(gross)
            slip["employee_id"] = e.get("id")
            slip["name"] = f"{e.get('first_name','')} {e.get('last_name','')}"
            results.append(slip)
        return results
