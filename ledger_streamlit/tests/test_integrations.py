
from ledger.integrations.connectors import QuickBooksConnector, ExcelConnector, APIConnector
import pandas as pd, json, tempfile

def test_quickbooks_connector():
    qb=QuickBooksConnector("demo-tenant")
    records=qb.fetch_invoices()
    assert isinstance(records,list) and records

def test_excel_connector(tmp_path):
    df=pd.DataFrame([{"date":"2025-09-12","amount":5000,"vendor":"Excel Vendor"}])
    path=tmp_path/"test.xlsx"
    df.to_excel(path,index=False)
    ex=ExcelConnector("demo-tenant")
    records=ex.load_excel(str(path))
    assert records and records[0]["vendor"]=="Excel Vendor"

def test_api_connector(requests_mock):
    url="http://fakeapi.com/data"
    requests_mock.get(url,json=[{"date":"2025-09-12","amount":7500,"vendor":"API Vendor"}])
    api=APIConnector("demo-tenant")
    records=api.fetch_from_api(url)
    assert records and records[0]["vendor"]=="API Vendor"
