
import json, numpy as np
from pathlib import Path
from ledger.ml.anomaly import AnomalyDetector
from ledger.ml.classifier import ClassifierWrapper

def test_anomaly_detects_outliers():
    f=next(Path(__file__).resolve().parents[2].glob("data/transactions/*_transactions.json"))
    tid=f.stem.split("_")[0]
    txs=json.load(open(f))
    ad=AnomalyDetector(tid)
    ad.train(txs,contamination=0.02)
    res=ad.score(txs)
    assert any(r["is_anomaly"] for r in res)

def test_classifier_basic():
    X=np.array([[1,2],[2,3],[100,5]])
    y=np.array([0,0,1])
    cw=ClassifierWrapper("testtenant")
    cw.train(X,y)
    out=cw.predict(np.array([[1.5,2.5],[150,6]]))
    assert "predictions" in out and len(out["predictions"])==2
