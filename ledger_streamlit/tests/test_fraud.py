
from ledger.ledger.posting import LedgerPosting
from ledger.ml.fraud import FraudDetector

def test_fraud_detection_flags_outliers():
    tid="demo-tenant"
    lp=LedgerPosting(tid)
    lp.post_entry("2025-01-01","Normal Txn","5000","1000",1000.0)
    lp.post_entry("2025-01-02","Big Txn","5000","1000",1000000.0)
    fd=FraudDetector(tid)
    df=fd.detect(contamination=0.5)
    assert "anomaly" in df.columns
    assert any(df["anomaly"]=="Suspicious")
