
from ledger.ingest.parser import IngestionParser
import pandas as pd
import tempfile, json

def test_parser_csv(tmp_path):
    df=pd.DataFrame([
      {"Date":"12/09/2025","Amount":"10,000","Vendor":"Eco Waste","Ref":"TX123"},
      {"Date":"13/09/2025","Amount":"5,500","Vendor":"KPLC","Ref":"TX124"}
    ])
    file=tmp_path/"sample.csv"; df.to_csv(file,index=False)
    parser=IngestionParser("demo-tenant")
    recs=parser.parse_file(str(file))
    assert len(recs)==2
    assert recs[0]["amount"]==10000.0
    path=parser.save_to_staging(recs)
    saved=json.load(open(path))
    assert saved[0]["vendor"]=="Eco Waste"
