
import json
import pandas as pd
import requests
from pathlib import Path

STAGING_DIR = Path(__file__).resolve().parents[2] / "data" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

class QuickBooksConnector:
    def __init__(self, tenant_id: str):
        self.tenant_id=tenant_id
    
    def test_connection(self) -> bool:
        """Test QuickBooks API connection."""
        # In real deployment, this would test OAuth2 connection
        return True

    def fetch_invoices(self) -> list:
        # Placeholder: In real deployment, integrate QuickBooks API with OAuth2.
        # For now, simulate.
        return [{"date":"2025-09-12","amount":10000.0,"vendor":"QuickBooks Vendor","reference":"QB123"}]

    def save_to_staging(self, records: list) -> Path:
        out=STAGING_DIR/f"{self.tenant_id}_staging.json"
        with open(out,"w",encoding="utf-8") as f: json.dump(records,f,indent=2)
        return out

class ExcelConnector:
    def __init__(self, tenant_id: str):
        self.tenant_id=tenant_id
    
    def test_connection(self) -> bool:
        """Test Excel file access."""
        return True

    def load_excel(self, path: str) -> list:
        df=pd.read_excel(path)
        records=df.to_dict(orient="records")
        out=STAGING_DIR/f"{self.tenant_id}_staging.json"
        with open(out,"w",encoding="utf-8") as f: json.dump(records,f,indent=2)
        return records

class APIConnector:
    def __init__(self, tenant_id: str):
        self.tenant_id=tenant_id
    
    def test_connection(self) -> bool:
        """Test API endpoint connectivity."""
        return True

    def fetch_from_api(self, url: str) -> list:
        try:
            r=requests.get(url,timeout=10)
            r.raise_for_status()
            data=r.json()
        except Exception as e:
            raise RuntimeError(f"API fetch failed: {e}")
        out=STAGING_DIR/f"{self.tenant_id}_staging.json"
        with open(out,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)
        return data
