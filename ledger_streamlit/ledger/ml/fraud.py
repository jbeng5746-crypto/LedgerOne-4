
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import IsolationForest

from ledger.ledger.posting import LedgerPosting

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FRAUD_DIR = DATA_DIR / "fraud"
FRAUD_DIR.mkdir(parents=True, exist_ok=True)

class FraudDetector:
    def __init__(self, tenant_id: str):
        self.tenant_id=tenant_id
        self.lp=LedgerPosting(tenant_id)

    def detect(self, contamination: float=0.05) -> pd.DataFrame:
        journal=self.lp.load_journal()
        if not journal: return pd.DataFrame()
        df=pd.DataFrame(journal)
        if df.empty: return df
        X=df[["amount"]].values
        clf=IsolationForest(contamination=contamination,random_state=42)
        df["anomaly"]=clf.fit_predict(X)
        df["anomaly"]=df["anomaly"].map({-1:"Suspicious",1:"Normal"})
        frauds=df[df["anomaly"]=="Suspicious"]
        out=FRAUD_DIR/f"{self.tenant_id}_fraud.json"
        frauds.to_json(out,orient="records",indent=2,date_format="iso")
        return df
