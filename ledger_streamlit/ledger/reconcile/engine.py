
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta

from ledger.ml.vendor_normalizer import VendorNormalizer

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RECON_DIR = DATA_DIR / "reconcile"
RECON_DIR.mkdir(parents=True, exist_ok=True)

class ReconciliationEngine:
    """
    Match ingested staging data against tenant ledger transactions.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.vn = VendorNormalizer(tenant_id)

    def load_staging(self) -> List[Dict[str, Any]]:
        f = DATA_DIR / "staging" / f"{self.tenant_id}_staging.json"
        if f.exists():
            return json.load(open(f))
        return []

    def load_transactions(self) -> List[Dict[str, Any]]:
        f = DATA_DIR / "transactions" / f"{self.tenant_id}_transactions.json"
        if f.exists():
            return json.load(open(f))
        return []

    def reconcile(self, date_tolerance_days: int = 2, amount_tolerance: float = 5.0) -> Dict[str, Any]:
        staging = self.load_staging()
        ledger = self.load_transactions()
        results = []
        ledger_used=set()
        for rec in staging:
            match=None; reason=[]
            # normalize vendor
            if rec.get("vendor"):
                try:
                    norm=self.vn.normalize(rec["vendor"])
                    rec["vendor_normalized"]=norm["canonical"]
                except: rec["vendor_normalized"]=rec["vendor"]

            for i,txn in enumerate(ledger):
                if i in ledger_used: continue
                # match amount
                amt_ok = abs((rec.get("amount") or 0) - (txn.get("amount") or 0)) <= amount_tolerance
                # match date
                try:
                    d1=datetime.fromisoformat(rec.get("date")) if rec.get("date") else None
                    d2=datetime.fromisoformat(txn.get("date")) if txn.get("date") else None
                except: d1=d2=None
                date_ok = (d1 and d2 and abs((d1-d2).days) <= date_tolerance_days)
                # match vendor
                vendor_ok = (rec.get("vendor_normalized") and txn.get("vendor") and rec["vendor_normalized"].lower()==txn["vendor"].lower())
                if amt_ok and date_ok and vendor_ok:
                    match=txn; ledger_used.add(i)
                    reason=["amount","date","vendor"]
                    break
                elif amt_ok and date_ok:
                    match=txn; ledger_used.add(i)
                    reason=["amount","date"]
                    break
            results.append({"staging":rec,"match":match,"reason":reason})
        report={"tenant_id":self.tenant_id,"matches":results,"unmatched":[r for r in results if not r["match"]]}
        out=RECON_DIR/f"{self.tenant_id}_recon.json"
        with open(out,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
        return report
