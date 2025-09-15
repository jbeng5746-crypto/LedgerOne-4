
import math
import joblib
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

MODELS_DIR = Path(__file__).resolve().parents[2] / "data" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def _features(transactions: List[Dict[str, Any]]):
    X = []
    for t in transactions:
        amt = float(t.get("amount",0))
        log_amt = math.log1p(abs(amt)) * (1 if amt>=0 else -1)
        dom = int(t.get("date_dom",1))
        vendor_len = len(t.get("vendor",""))
        X.append([log_amt, dom, vendor_len])
    return np.array(X)

class AnomalyDetector:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.model_path = MODELS_DIR / f"anomaly_{tenant_id}.joblib"
        self.scaler_path = MODELS_DIR / f"anomaly_{tenant_id}_scaler.joblib"
        self.model=None; self.scaler=None

    def train(self, transactions: List[Dict[str, Any]], contamination:float=0.01):
        X = _features(transactions)
        self.scaler = StandardScaler().fit(X)
        Xs = self.scaler.transform(X)
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.model.fit(Xs)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        return {"model":str(self.model_path)}

    def load(self):
        self.model = joblib.load(self.model_path)
        self.scaler = joblib.load(self.scaler_path)
        return True

    def score(self, transactions: List[Dict[str, Any]]):
        if self.model is None: self.load()
        X = _features(transactions)
        Xs = self.scaler.transform(X)
        scores = self.model.score_samples(Xs)
        preds = self.model.predict(Xs)
        return [{"id":t.get("id"),"score":float(s),"is_anomaly":(int(p)==-1)}
                for t,s,p in zip(transactions,scores,preds)]
