
from ledger.ledger.posting import LedgerPosting
from ledger.reports.financials import FinancialReports
import tempfile, json

def test_trial_balance_and_reports(tmp_path):
    tid="demo-tenant"
    lp=LedgerPosting(tid)
    lp.post_entry("2025-09-12","Sale","1000","4000",5000.0,"TX001")
    lp.post_entry("2025-09-12","Expense","5000","1000",2000.0,"TX002")
    fr=FinancialReports(tid)
    tb=fr.trial_balance()
    assert not tb.empty
    bs=fr.balance_sheet()
    assert "Assets" in bs and "Balanced" in bs
    pl=fr.profit_and_loss()
    assert abs(pl["Revenue"]-5000.0)<0.01
    assert abs(pl["Expenses"]-2000.0)<0.01
