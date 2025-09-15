
import re, json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

try:
    import pytesseract
    from PIL import Image
    import pdf2image
    OCR_AVAILABLE = True
except ImportError:
    pytesseract = None
    Image = None
    pdf2image = None
    OCR_AVAILABLE = False

STAGING_DIR = Path(__file__).resolve().parents[2] / "data" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

class OCRIngestion:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def extract_text(self, file_path: str) -> str:
        """Extract text from PDF or image using Tesseract."""
        if not OCR_AVAILABLE:
            # fallback: simulate
            return open(file_path,"r",encoding="utf-8").read()
        suffix=Path(file_path).suffix.lower()
        if suffix in [".png",".jpg",".jpeg",".tiff"]:
            if Image is None:
                raise RuntimeError("PIL not available")
            img = Image.open(file_path)
            if pytesseract is None:
                raise RuntimeError("pytesseract not available")
            return pytesseract.image_to_string(img)
        elif suffix in [".pdf"]:
            if pdf2image is None or pytesseract is None:
                raise RuntimeError("pdf2image or pytesseract not available")
            pages = pdf2image.convert_from_path(file_path)
            texts = [pytesseract.image_to_string(p) for p in pages]
            return "\n".join(texts)
        else:
            raise ValueError("Unsupported file type for OCR")

    def parse_invoice_text(self, text: str) -> Dict[str, Any]:
        """Parse key fields from invoice text using regex heuristics (Kenyan style)."""
        out={"vendor":None,"date":None,"invoice_no":None,"total":None,"currency":"KES"}
        # Vendor
        m=re.search(r"(?i)invoice\s+from[:\s]+([A-Za-z0-9 &]+)",text)
        if m: out["vendor"]=m.group(1).strip()
        else:
            lines=text.splitlines()
            if lines: out["vendor"]=lines[0].strip()

        # Invoice No
        m=re.search(r"(?i)invoice\s*(no|#)[:\s]+(\w+)",text)
        if m: out["invoice_no"]=m.group(2)

        # Date
        m=re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",text)
        if m:
            try:
                out["date"]=datetime.strptime(m.group(1),"%d/%m/%Y").strftime("%Y-%m-%d")
            except:
                try: out["date"]=datetime.strptime(m.group(1),"%d-%m-%Y").strftime("%Y-%m-%d")
                except: out["date"]=m.group(1)

        # Total
        m=re.search(r"(?i)total[:\s]+([\d,]+(\.\d{1,2})?)",text)
        if m:
            amt=m.group(1).replace(",","")
            try: out["total"]=float(amt)
            except: pass
        return out

    def process_file(self, file_path: str) -> Dict[str, Any]:
        text=self.extract_text(file_path)
        parsed=self.parse_invoice_text(text)
        out={"tenant_id":self.tenant_id,"raw_text":text,"parsed":parsed}
        outpath=STAGING_DIR/f"{self.tenant_id}_ocr.json"
        with open(outpath,"w",encoding="utf-8") as f: json.dump(out,f,indent=2)
        return out
