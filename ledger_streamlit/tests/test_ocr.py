
from ledger.ingest.ocr import OCRIngestion
import tempfile, json

def test_parse_invoice_text():
    sample_text = """Invoice From: EcoWaste Ltd
Invoice No: INV123
Date: 12/09/2025
Total: 15,500.00 KES
"""
    ocr=OCRIngestion("demo-tenant")
    parsed=ocr.parse_invoice_text(sample_text)
    assert parsed["vendor"]=="EcoWaste Ltd"
    assert parsed["invoice_no"]=="INV123"
    assert parsed["total"]==15500.00
