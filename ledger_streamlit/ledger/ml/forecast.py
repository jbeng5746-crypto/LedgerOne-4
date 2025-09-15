
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any

try:
    from prophet import Prophet
    PROPHET_AVAILABLE=True
except ImportError:
    PROPHET_AVAILABLE=False

try:
    from xgboost import XGBRegressor
    XGB_AVAILABLE=True
except ImportError:
    XGB_AVAILABLE=False

from ledger.ledger.posting import LedgerPosting

class ForecastEngine:
    def __init__(self, tenant_id: str):
        self.tenant_id=tenant_id
        self.lp=LedgerPosting(tenant_id)

    def load_monthly(self) -> pd.DataFrame:
        journal=self.lp.load_journal()
        if not journal: return pd.DataFrame(columns=["date","amount","type"])
        df=pd.DataFrame(journal)
        df["date"]=pd.to_datetime(df["date"])
        # classify revenue vs expense by account codes
        df["type"]=np.where(df["credit_acct"].str.startswith("4"),"Revenue",
                    np.where(df["debit_acct"].str.startswith("5"),"Expense","Other"))
        agg=df.groupby([pd.Grouper(key="date",freq="M"),"type"])["amount"].sum().reset_index()
        return agg

    def forecast(self, series: pd.DataFrame, periods:int=12) -> pd.DataFrame:
        if series.empty: return pd.DataFrame()
        df=series.rename(columns={"date":"ds","amount":"y"})
        if PROPHET_AVAILABLE:
            m=Prophet()
            m.fit(df)
            future=m.make_future_dataframe(periods=periods,freq="M")
            fcst=m.predict(future)
            return fcst[["ds","yhat","yhat_lower","yhat_upper"]]
        elif XGB_AVAILABLE:
            df["t"]=range(len(df))
            X=df[["t"]]; y=df["y"]
            model=XGBRegressor(n_estimators=100)
            model.fit(X,y)
            future=pd.DataFrame({"t":range(len(df),len(df)+periods)})
            preds=model.predict(future)
            future["yhat"]=preds
            future["ds"]=pd.date_range(df["ds"].iloc[-1],periods=periods+1,freq="M")[1:]
            return future[["ds","yhat"]]
        else:
            # fallback naive forecast: repeat last value
            last=df["y"].iloc[-1]
            dates=pd.date_range(df["ds"].iloc[-1],periods=periods+1,freq="M")[1:]
            return pd.DataFrame({"ds":dates,"yhat":[last]*periods})

    def forecast_revenue_expenses(self, periods:int=12) -> Dict[str,pd.DataFrame]:
        data=self.load_monthly()
        results={}
        for t in ["Revenue","Expense"]:
            series=data[data["type"]==t][["date","amount"]]
            if not series.empty:
                results[t]=self.forecast(series,periods)
        return results
