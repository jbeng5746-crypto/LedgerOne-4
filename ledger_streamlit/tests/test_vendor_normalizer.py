
import json
from pathlib import Path
from ledger.ml.vendor_normalizer import VendorNormalizer, VENDORS_DIR

def test_train_and_normalize():
    vf = next(Path(VENDORS_DIR).glob("*_vendors.json"))
    tid = vf.stem.split("_")[0]
    vendors=json.load(open(vf))
    vn=VendorNormalizer(tenant_id=tid)
    vn.train(vendors); vn.save()
    vn2=VendorNormalizer(tenant_id=tid); vn2.load()
    sample=vendors[0]; variant=sample.upper()
    res=vn2.normalize(variant)
    assert res["canonical"] is not None or res["method"] in ("fuzzy","none")
    res2=vn2.normalize("Completely Unknown Vendor XYZ")
    assert res2["canonical"] is None
