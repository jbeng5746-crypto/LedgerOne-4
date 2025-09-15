
import os, json, uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from fuzzywuzzy import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import joblib

MODELS_DIR = Path(__file__).resolve().parents[2] / "data" / "models"
VENDORS_DIR = Path(__file__).resolve().parents[2] / "data" / "vendors"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
VENDORS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class ModelMeta:
    model_id: str
    tenant_id: str
    created_at: str
    vectorizer_file: str
    nn_file: str
    vendor_list_file: str
    def to_dict(self): return asdict(self)

class VendorNormalizer:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.vectorizer = None
        self.nn = None
        self.vendor_list: List[str] = []
        self.meta: Optional[ModelMeta] = None

    def _model_base(self): return MODELS_DIR / f"vendor_{self.tenant_id}"

    def train(self, vendors: List[str]):
        vendors = list(dict.fromkeys([v.strip() for v in vendors if v]))
        self.vendor_list = vendors
        self.vectorizer = TfidfVectorizer(ngram_range=(1,2)).fit(vendors)
        X = self.vectorizer.transform(vendors)
        self.nn = NearestNeighbors(n_neighbors=1, metric="cosine").fit(X)
        self.meta = ModelMeta(
            model_id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            created_at=__import__("time").ctime(),
            vectorizer_file=str(self._model_base())+"_vec.joblib",
            nn_file=str(self._model_base())+"_nn.joblib",
            vendor_list_file=str(self._model_base())+"_vendors.json"
        )
        return self.meta

    def save(self):
        if not self.meta: raise RuntimeError("Train before save")
        joblib.dump(self.vectorizer, self.meta.vectorizer_file)
        joblib.dump(self.nn, self.meta.nn_file)
        with open(self.meta.vendor_list_file,"w") as f: json.dump(self.vendor_list,f,indent=2)
        with open(Path(self.meta.vectorizer_file).with_suffix(".meta.json"),"w") as f: json.dump(self.meta.to_dict(),f,indent=2)
        return self.meta.to_dict()

    def load(self):
        base=self._model_base()
        vec_file=str(base)+"_vec.joblib"
        nn_file=str(base)+"_nn.joblib"
        vendors_file=str(base)+"_vendors.json"
        self.vectorizer=joblib.load(vec_file)
        self.nn=joblib.load(nn_file)
        with open(vendors_file) as f: self.vendor_list=json.load(f)
        return True

    def normalize(self, raw_name: str, *, fuzzy_threshold:int=75) -> Dict[str,Any]:
        name=(raw_name or "").strip()
        if not name: return {"input":raw_name,"canonical":None,"score":0.0,"method":"none"}
        if self.vectorizer and self.nn and self.vendor_list:
            vec=self.vectorizer.transform([name])
            dist,ind=self.nn.kneighbors(vec,n_neighbors=1)
            sim=1.0-float(dist[0][0])
            cand=self.vendor_list[int(ind[0][0])]
            if sim>=0.6:
                return {"input":raw_name,"canonical":cand,"score":sim,"method":"nn"}
        best=None; best_score=0
        for v in self.vendor_list:
            s=fuzz.token_set_ratio(name,v)
            if s>best_score: best, best_score=v, s
        if best_score>=fuzzy_threshold:
            return {"input":raw_name,"canonical":best,"score":best_score/100.0,"method":"fuzzy"}
        return {"input":raw_name,"canonical":None,"score":0.0,"method":"none"}
