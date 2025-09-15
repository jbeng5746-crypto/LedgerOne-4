
from ledger.ingest.engine import IngestionEngine
import pandas as pd, json

def test_engine_structured(tmp_path):
    df=pd.DataFrame([{"Date":"12/09/2025","Amount":"5000","Vendor":"Safaricom"}])
    file=tmp_path/"s.csv"; df.to_csv(file,index=False)
    eng=IngestionEngine("demo-tenant")
    res=eng.ingest(str(file))
    assert res["mode"]=="structured"
    data=json.load(open(res["file"]))
    assert data[0]["vendor"]=="Safaricom"

def test_engine_ocr(tmp_path):
    # simulate OCR by writing text file (since Tesseract may not be installed)
    txtfile=tmp_path/"inv.txt"
    txtfile.write_text("Invoice From: KPLC\nInvoice No: 999\nDate: 12/09/2025\nTotal: 1,200.00 KES")
    eng=IngestionEngine("demo-tenant")
    # OCRIngestion fallback will read raw text
    res=eng.ingest(str(txtfile))
    assert res["mode"]=="ocr"
    parsed=res["parsed"]
    assert parsed["vendor"]=="KPLC"
    assert parsed["total"]==1200.00
