
from ledger.tax.payroll import KenyanPayroll, KenyanVAT

def test_paye_bands():
    p=KenyanPayroll()
    assert p.compute_paye(20000) < p.compute_paye(100000)

def test_nssf_and_nhif():
    p=KenyanPayroll()
    assert p.compute_nssf(10000) > 0
    assert p.compute_nhif(15000)==500

def test_payroll_breakdown():
    p=KenyanPayroll()
    b=p.payroll_breakdown(50000)
    assert b["Gross"]==50000
    assert b["Net"]<50000

def test_vat():
    v=KenyanVAT()
    assert v.compute_vat(1000)==160.0
