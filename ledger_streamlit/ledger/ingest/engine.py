
import json
from pathlib import Path
from typing import Dict, Any

from .parser import IngestionParser
from .ocr import OCRIngestion

STAGING_DIR = Path(__file__).resolve().parents[2] / "data" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

class IngestionEngine:
    """
    Unified ingestion engine for structured files and OCR files.
    """
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.parser = IngestionParser(tenant_id)
        self.ocr = OCRIngestion(tenant_id)

    def ingest(self, file_path: str) -> Dict[str, Any]:
        ext = Path(file_path).suffix.lower()
        if ext in [".csv",".xls",".xlsx",".json"]:
            records = self.parser.parse_file(file_path)
            path = self.parser.save_to_staging(records)
            return {"mode":"structured","count":len(records),"file":str(path)}
        elif ext in [".pdf",".png",".jpg",".jpeg",".tiff"]:
            res = self.ocr.process_file(file_path)
            return {"mode":"ocr","parsed":res["parsed"],"file":str(STAGING_DIR/f"{self.tenant_id}_ocr.json")}
        else:
            raise ValueError(f"Unsupported file type: {ext}")
