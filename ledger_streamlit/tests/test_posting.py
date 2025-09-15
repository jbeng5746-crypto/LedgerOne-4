
from ledger.ledger.posting import LedgerPosting, CHART_OF_ACCOUNTS
import json, tempfile

def test_post_entry_and_journal(tmp_path):
    tid="demo-tenant"
    lp=LedgerPosting(tid)
    e=lp.post_entry("2025-09-12","Test Entry","5000","1000",2000.0,"TX999")
    assert e["amount"]==2000.0
    j=lp.load_journal()
    assert any(x["ref"]=="TX999" for x in j)

def test_post_from_reconciliation(tmp_path):
    tid="demo-tenant"
    recon={"tenant_id":tid,"matches":[{"staging":{"date":"2025-09-12","amount":1000.0,"vendor":"KPLC","reference":"TX123"},"match":{"date":"2025-09-12","amount":1000.0,"vendor":"kplc"},"reason":["amount","date","vendor"]}]}
    recon_file=tmp_path/f"{tid}_recon.json"
    recon_file.write_text(json.dumps(recon))
    lp=LedgerPosting(tid)
    posted=lp.post_from_reconciliation(recon_file)
    assert posted and posted[0]["amount"]==1000.0
