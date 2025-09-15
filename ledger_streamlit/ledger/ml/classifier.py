
import joblib
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parents[2] / "data" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def _backend():
    try:
        import xgboost; return "xgboost"
    except:
        try: import lightgbm; return "lightgbm"
        except: return "sklearn"

class ClassifierWrapper:
    def __init__(self, tenant_id:str):
        self.tenant_id=tenant_id
        self.model_path = MODELS_DIR/f"classifier_{tenant_id}.joblib"
        self.model=None

    def train(self,X,y):
        mode=_backend()
        if mode=="xgboost":
            import xgboost as xgb
            self.model=xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss')
        elif mode=="lightgbm":
            import lightgbm as lgb
            self.model=lgb.LGBMClassifier()
        else:
            from sklearn.ensemble import GradientBoostingClassifier
            self.model=GradientBoostingClassifier()
        self.model.fit(X,y)
        joblib.dump(self.model,self.model_path)
        return {"model":str(self.model_path),"backend":mode}

    def load(self):
        self.model=joblib.load(self.model_path); return True

    def predict(self,X):
        if self.model is None: self.load()
        preds=self.model.predict(X)
        probs=self.model.predict_proba(X).tolist() if hasattr(self.model,"predict_proba") else None
        return {"predictions":preds.tolist() if hasattr(preds,"tolist") else list(preds),"probabilities":probs}
