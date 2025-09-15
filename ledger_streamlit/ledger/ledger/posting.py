
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
LEDGER_DIR = DATA_DIR / "ledger"
LEDGER_DIR.mkdir(parents=True, exist_ok=True)

# Basic Chart of Accounts (Kenya context)
CHART_OF_ACCOUNTS = {
    "1000": "Assets:Cash/Bank",
    "2000": "Liabilities:Accounts Payable",
    "2100": "Liabilities:VAT Payable",
    "2200": "Liabilities:PAYE",
    "2210": "Liabilities:NSSF",
    "2220": "Liabilities:NHIF",
    "3000": "Equity:Capital",
    "4000": "Revenue:Sales",
    "5000": "Expenses:General",
    "5100": "Expenses:Payroll",
    "5200": "Expenses:Fleet",
}

class LedgerPosting:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.file = LEDGER_DIR / f"{tenant_id}_journal.json"
        if not self.file.exists():
            with open(self.file,"w",encoding="utf-8") as f: json.dump([],f)

    def load_journal(self) -> List[Dict[str, Any]]:
        return json.load(open(self.file,"r",encoding="utf-8"))

    def post_entry(self, date: str, description: str, debit_acct: str, credit_acct: str, amount: float, ref: str=None) -> Dict[str,Any]:
        entry={
            "date":date,
            "description":description,
            "debit_acct":debit_acct,
            "credit_acct":credit_acct,
            "amount":amount,
            "ref":ref,
            "created_at":datetime.utcnow().isoformat()+"Z"
        }
        journal=self.load_journal()
        journal.append(entry)
        with open(self.file,"w",encoding="utf-8") as f: json.dump(journal,f,indent=2)
        return entry

    def post_from_reconciliation(self, recon_file: Path) -> List[Dict[str,Any]]:
        if not Path(recon_file).exists():
            raise FileNotFoundError("Reconciliation file not found")
        report=json.load(open(recon_file,"r",encoding="utf-8"))
        posted=[]
        for m in report.get("matches",[]):
            if not m.get("match"): continue
            rec=m["staging"]
            date=rec.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
            amt=rec.get("amount") or 0.0
            vendor=rec.get("vendor_normalized") or rec.get("vendor")
            desc=f"Payment to {vendor}"
            # Simple rule: Payments reduce bank, increase expense
            debit="5000"  # Expenses:General
            credit="1000" # Assets:Cash/Bank
            entry=self.post_entry(date,desc,debit,credit,amt,ref=rec.get("reference"))
            posted.append(entry)
        return posted
    
    def get_chart_of_accounts(self) -> Dict[str, str]:
        """Return the chart of accounts"""
        return CHART_OF_ACCOUNTS.copy()
    
    def get_trial_balance(self) -> Dict[str, float]:
        """Calculate trial balance from journal entries"""
        journal = self.load_journal()
        balances = {}
        
        for entry in journal:
            debit_acct = entry.get("debit_acct", "")
            credit_acct = entry.get("credit_acct", "")
            amount = float(entry.get("amount", 0))
            
            # Debit increases asset/expense accounts, decreases liability/equity/revenue
            if debit_acct in balances:
                balances[debit_acct] += amount
            else:
                balances[debit_acct] = amount
                
            # Credit decreases asset/expense accounts, increases liability/equity/revenue  
            if credit_acct in balances:
                balances[credit_acct] -= amount
            else:
                balances[credit_acct] = -amount
                
        return balances
    
    def get_balance_by_account_type(self, account_type: str) -> float:
        """Get total balance for account type (Assets, Liabilities, Equity, Revenue, Expenses)"""
        balances = self.get_trial_balance()
        total = 0.0
        
        for acct_code, balance in balances.items():
            if acct_code in CHART_OF_ACCOUNTS:
                acct_name = CHART_OF_ACCOUNTS[acct_code]
                if acct_name.startswith(account_type):
                    total += balance
                    
        return total
