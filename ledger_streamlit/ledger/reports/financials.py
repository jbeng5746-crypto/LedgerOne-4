
import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

from ledger.ledger.posting import CHART_OF_ACCOUNTS, LedgerPosting

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

class FinancialReports:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.lp = LedgerPosting(tenant_id)

    def load_journal_df(self) -> pd.DataFrame:
        journal = self.lp.load_journal()
        if not journal: return pd.DataFrame(columns=["date","debit_acct","credit_acct","amount"])
        return pd.DataFrame(journal)

    def trial_balance(self) -> pd.DataFrame:
        df=self.load_journal_df()
        if df.empty: return pd.DataFrame(columns=["Account","Debit","Credit"])
        tb={}
        for _,row in df.iterrows():
            tb.setdefault(row["debit_acct"],{"debit":0.0,"credit":0.0})
            tb[row["debit_acct"]]["debit"]+=row["amount"]
            tb.setdefault(row["credit_acct"],{"debit":0.0,"credit":0.0})
            tb[row["credit_acct"]]["credit"]+=row["amount"]
        rows=[]
        for acct,vals in tb.items():
            rows.append({"Account":f"{acct} {CHART_OF_ACCOUNTS.get(acct,'Unknown')}",
                         "Debit":vals["debit"],"Credit":vals["credit"]})
        return pd.DataFrame(rows)

    def balance_sheet(self) -> Dict[str,Any]:
        tb=self.trial_balance()
        assets=tb[tb["Account"].str.startswith("1000")]["Debit"].sum()-tb[tb["Account"].str.startswith("1000")]["Credit"].sum()
        liabs=tb[tb["Account"].str.startswith("2")]["Credit"].sum()-tb[tb["Account"].str.startswith("2")]["Debit"].sum()
        equity=tb[tb["Account"].str.startswith("3")]["Credit"].sum()-tb[tb["Account"].str.startswith("3")]["Debit"].sum()
        return {"Assets":assets,"Liabilities":liabs,"Equity":equity,"Balanced":round(assets,2)==round(liabs+equity,2)}

    def profit_and_loss(self) -> Dict[str,float]:
        tb=self.trial_balance()
        revenue=tb[tb["Account"].str.startswith("4")]["Credit"].sum()-tb[tb["Account"].str.startswith("4")]["Debit"].sum()
        expenses=tb[tb["Account"].str.startswith("5")]["Debit"].sum()-tb[tb["Account"].str.startswith("5")]["Credit"].sum()
        return {"Revenue":revenue,"Expenses":expenses,"NetIncome":revenue-expenses}
