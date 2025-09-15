
from ledger.reconcile.engine import ReconciliationEngine
import json, tempfile

def test_reconcile_matches(tmp_path):
    tid="demo-tenant"
    data_dir=tmp_path
    (data_dir/"staging").mkdir()
    (data_dir/"transactions").mkdir()
    # staging: 1 record
    staging=[{"date":"2025-09-12","amount":1000.0,"vendor":"KPLC"}]
    (data_dir/"staging"/f"{tid}_staging.json").write_text(json.dumps(staging))
    # ledger: 1 record with same
    ledger=[{"date":"2025-09-12","amount":1000.0,"vendor":"kplc"}]
    (data_dir/"transactions"/f"{tid}_transactions.json").write_text(json.dumps(ledger))

    import sys; sys.path.insert(0,str(data_dir.parent))
    from ledger.reconcile.engine import ReconciliationEngine
    eng=ReconciliationEngine(tid)
    eng.DATA_DIR=data_dir
    report=eng.reconcile()
    assert any(r["match"] for r in report["matches"])
