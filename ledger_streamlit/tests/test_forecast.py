
from ledger.ledger.posting import LedgerPosting
from ledger.ml.forecast import ForecastEngine

def test_forecast_returns_results():
    tid="demo-tenant"
    lp=LedgerPosting(tid)
    lp.post_entry("2025-01-01","Sale","1000","4000",10000.0)
    lp.post_entry("2025-02-01","Expense","5000","1000",5000.0)
    fe=ForecastEngine(tid)
    res=fe.forecast_revenue_expenses(periods=3)
    assert "Revenue" in res or "Expense" in res
    for df in res.values():
        assert not df.empty
