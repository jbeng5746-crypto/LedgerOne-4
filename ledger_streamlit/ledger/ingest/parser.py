
import pandas as pd
import re, json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

STAGING_DIR = Path(__file__).resolve().parents[2] / "data" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

class IngestionParser:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def _normalize_date(self, val: Any) -> str:
        """Try to parse Kenyan-style date formats to ISO YYYY-MM-DD."""
        if pd.isna(val): return None
        if isinstance(val, datetime):
            return val.strftime("%Y-%m-%d")
        if isinstance(val, (int, float)):
            try:
                return pd.to_datetime(val, origin="1899-12-30", unit="D").strftime("%Y-%m-%d")
            except: return None
        s = str(val).strip()
        # Try day/month/year
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d %B %Y"]:
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            except: continue
        try:
            return pd.to_datetime(s, dayfirst=True, errors="coerce").strftime("%Y-%m-%d")
        except: return None

    def _normalize_amount(self, val: Any) -> float:
        if pd.isna(val): return None
        try:
            return float(str(val).replace(",", "").replace("KES","").strip())
        except: return None

    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse CSV, Excel, or JSON into normalized transaction dicts."""
        ext = Path(file_path).suffix.lower()
        if ext in [".csv"]:
            df = pd.read_csv(file_path)
        elif ext in [".xls",".xlsx"]:
            df = pd.read_excel(file_path)
        elif ext in [".json"]:
            return json.load(open(file_path,"r"))
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        df = df.rename(columns={c.lower().strip():c for c in df.columns})
        records=[]
        for _, row in df.iterrows():
            rec={
              "date": None,
              "vendor": None,
              "amount": None,
              "description": None,
              "reference": None,
              "currency": "KES"
            }
            # detect fields
            for col,val in row.items():
                col_l=col.lower()
                if any(k in col_l for k in ["date","txn","time"]):
                    rec["date"]=self._normalize_date(val)
                elif any(k in col_l for k in ["amount","kes","debit","credit"]):
                    rec["amount"]=self._normalize_amount(val)
                elif any(k in col_l for k in ["vendor","payee","name","beneficiary","from","to"]):
                    rec["vendor"]=str(val).strip() if not pd.isna(val) else None
                elif any(k in col_l for k in ["desc","narration","details","particulars"]):
                    rec["description"]=str(val).strip() if not pd.isna(val) else None
                elif any(k in col_l for k in ["ref","cheque","id","transaction no"]):
                    rec["reference"]=str(val).strip() if not pd.isna(val) else None
            if rec["date"] or rec["amount"]:
                records.append(rec)
        return records

    def save_to_staging(self, records: List[Dict[str, Any]]):
        path=STAGING_DIR/f"{self.tenant_id}_staging.json"
        with open(path,"w",encoding="utf-8") as f: json.dump(records,f,indent=2)
        return str(path)
