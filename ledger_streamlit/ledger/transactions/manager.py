"""
Transaction Management with bulk upload, reconciliation integration, and journal posting.
"""
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.upload_manager import UploadManager, ColumnMapping, UploadResult
from ..core.repositories import TransactionsRepository
from ..reconcile.engine import ReconciliationEngine
from ..ledger.posting import LedgerPosting

class TransactionManager:
    """Comprehensive transaction management with bulk operations and reconciliation."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.repository = TransactionsRepository(tenant_id)
        self.upload_manager = UploadManager(tenant_id, 'transactions')
        self.reconcile_engine = ReconciliationEngine(tenant_id)
        self.ledger_posting = LedgerPosting(tenant_id)
    
    def get_template(self) -> pd.DataFrame:
        """Get transaction upload template."""
        return self.upload_manager.generate_template()
    
    def bulk_upload(
        self, 
        file_path: str,
        column_mappings: List[Dict[str, str]],
        mode: str = 'append',
        auto_reconcile: bool = False,
        auto_post: bool = False
    ) -> Dict[str, Any]:
        """
        Bulk upload transactions with reconciliation and posting integration.
        
        Args:
            file_path: Path to CSV/Excel/JSON file
            column_mappings: List of {'source': 'col_name', 'target': 'transaction_field'}
            mode: 'append', 'upsert', or 'replace'
            auto_reconcile: Whether to auto-run reconciliation after upload
            auto_post: Whether to auto-post to ledger after reconciliation
        """
        
        # Convert mappings to ColumnMapping objects
        mappings = [
            ColumnMapping(
                source_column=m['source'],
                target_field=m['target'],
                transform=m.get('transform')
            )
            for m in column_mappings
        ]
        
        # Custom transformation for transaction data
        def transform_transaction_data(df: pd.DataFrame) -> pd.DataFrame:
            """Apply transaction-specific transformations."""
            
            # Standardize vendor names
            if 'vendor' in df.columns:
                df['vendor'] = df['vendor'].str.strip()
            
            # Ensure amounts are numeric
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            
            if 'tax_amount' in df.columns:
                df['tax_amount'] = pd.to_numeric(df['tax_amount'], errors='coerce').fillna(0)
            
            if 'net_amount' in df.columns:
                df['net_amount'] = pd.to_numeric(df['net_amount'], errors='coerce')
            else:
                # Calculate net amount if not provided
                df['net_amount'] = df.get('amount', 0) - df.get('tax_amount', 0)
            
            # Standardize dates
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            
            # Set defaults
            df['currency'] = df.get('currency', 'KES')
            df['exchange_rate'] = pd.to_numeric(df.get('exchange_rate', 1.0), errors='coerce').fillna(1.0)
            df['status'] = df.get('status', 'pending')
            
            # Clean description
            if 'description' in df.columns:
                df['description'] = df['description'].str.strip()
            
            return df
        
        # Process upload
        upload_result = self.upload_manager.process_upload(
            file_path=file_path,
            mappings=mappings,
            mode=mode,
            transform_fn=transform_transaction_data
        )
        
        if not upload_result.success:
            return {
                'success': False,
                'upload_result': upload_result.to_dict(),
                'transaction_stats': None,
                'reconciliation_result': None,
                'posting_result': None
            }
        
        # Load staged data and commit to repository
        staging_file = self.upload_manager.staging_dir / f"{self.tenant_id}_transactions_{upload_result.batch_id}.json"
        with open(staging_file, 'r') as f:
            import json
            staged_data = json.load(f)
        
        transactions_data = staged_data['data']
        
        # Bulk upsert to repository
        repo_result = self.repository.bulk_upsert(transactions_data)
        
        reconciliation_result = None
        posting_result = None
        
        # Auto-reconcile if requested
        if auto_reconcile:
            try:
                reconciliation_result = self.reconcile_engine.reconcile()
            except Exception as e:
                reconciliation_result = {'error': str(e)}
        
        # Auto-post if requested and reconciliation succeeded
        if auto_post and reconciliation_result and not reconciliation_result.get('error'):
            try:
                posting_result = self._auto_post_transactions(transactions_data)
            except Exception as e:
                posting_result = {'error': str(e)}
        
        return {
            'success': True,
            'upload_result': upload_result.to_dict(),
            'transaction_stats': repo_result,
            'reconciliation_result': reconciliation_result,
            'posting_result': posting_result,
            'total_transactions': self.repository.get_count()
        }
    
    def _auto_post_transactions(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Auto-post transactions to ledger with smart account mapping."""
        
        posted_count = 0
        failed_count = 0
        errors = []
        
        for txn in transactions:
            try:
                # Determine accounts based on transaction type and category
                debit_acct, credit_acct = self._determine_accounts(txn)
                
                if debit_acct and credit_acct:
                    # Post to ledger
                    self.ledger_posting.post_entry(
                        date=txn.get('date'),
                        debit_acct=debit_acct,
                        credit_acct=credit_acct,
                        amount=float(txn.get('amount', 0)),
                        description=txn.get('description', ''),
                        reference=txn.get('reference', '')
                    )
                    posted_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Could not determine accounts for transaction: {txn.get('description', 'Unknown')}")
                    
            except Exception as e:
                failed_count += 1
                errors.append(f"Error posting transaction {txn.get('transaction_id', 'Unknown')}: {str(e)}")
        
        return {
            'posted_count': posted_count,
            'failed_count': failed_count,
            'errors': errors[:10]  # Limit errors shown
        }
    
    def _determine_accounts(self, transaction: Dict[str, Any]) -> tuple[str, str]:
        """
        Determine debit and credit accounts based on transaction data.
        Returns (debit_account, credit_account) or (None, None) if cannot determine.
        """
        
        amount = float(transaction.get('amount', 0))
        category = transaction.get('category', '').lower()
        account_code = transaction.get('account_code')
        description = transaction.get('description', '').lower()
        
        # If account code is provided, use it
        if account_code:
            if amount < 0:  # Credit transaction (money out)
                return '1000', account_code  # Cash -> Expense/Asset
            else:  # Debit transaction (money in) 
                return account_code, '1000'  # Revenue/Asset -> Cash
        
        # Smart mapping based on category and description
        if 'office' in category or 'office' in description:
            return '5200', '1000'  # Office Expenses -> Cash
        elif 'travel' in category or 'travel' in description:
            return '5300', '1000'  # Travel Expenses -> Cash
        elif 'salary' in category or 'payroll' in description:
            return '5100', '1000'  # Salaries -> Cash
        elif 'rent' in category or 'rent' in description:
            return '5400', '1000'  # Rent -> Cash
        elif 'sale' in category or 'revenue' in description or amount > 0:
            return '1000', '4000'  # Cash -> Sales Revenue
        elif amount < 0:  # General expense
            return '5000', '1000'  # General Expenses -> Cash
        else:
            return None, None  # Cannot determine
    
    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get transaction statistics and analytics."""
        transactions = self.repository.load_data()
        
        if not transactions:
            return {
                'total_transactions': 0,
                'by_status': {},
                'by_category': {},
                'by_currency': {},
                'total_amount': 0,
                'average_amount': 0
            }
        
        # Status breakdown
        status_counts = {}
        for txn in transactions:
            status = txn.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Category breakdown
        category_counts = {}
        for txn in transactions:
            category = txn.get('category', 'uncategorized')
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Currency breakdown
        currency_counts = {}
        for txn in transactions:
            currency = txn.get('currency', 'KES')
            currency_counts[currency] = currency_counts.get(currency, 0) + 1
        
        # Amount analysis (KES only)
        kes_amounts = [
            float(txn.get('amount', 0)) 
            for txn in transactions 
            if txn.get('currency', 'KES') == 'KES' and txn.get('amount')
        ]
        
        total_amount = sum(kes_amounts)
        avg_amount = total_amount / len(kes_amounts) if kes_amounts else 0
        
        return {
            'total_transactions': len(transactions),
            'by_status': status_counts,
            'by_category': category_counts,
            'by_currency': currency_counts,
            'total_amount': round(total_amount, 2),
            'average_amount': round(avg_amount, 2)
        }
    
    def search_transactions(
        self, 
        query: str = "", 
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search transactions with filters."""
        transactions = self.repository.load_data()
        
        # Apply filters
        if status:
            transactions = [t for t in transactions if t.get('status') == status]
        
        if start_date:
            transactions = [t for t in transactions if t.get('date', '') >= start_date]
        
        if end_date:
            transactions = [t for t in transactions if t.get('date', '') <= end_date]
        
        # Apply text search
        if query:
            query_lower = query.lower()
            filtered = []
            for txn in transactions:
                if (query_lower in txn.get('description', '').lower() or
                    query_lower in txn.get('vendor', '').lower() or
                    query_lower in txn.get('reference', '').lower() or
                    query_lower in txn.get('transaction_id', '').lower()):
                    filtered.append(txn)
            transactions = filtered
        
        # Sort by date (newest first)
        transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return transactions[:limit]
    
    def export_transactions(self, file_path: str, **filters) -> bool:
        """Export transactions to Excel file with optional filters."""
        transactions = self.search_transactions(**filters)
        
        if not transactions:
            return False
        
        df = pd.DataFrame(transactions)
        df.to_excel(file_path, index=False)
        return True
    
    def get_upload_history(self) -> List[Dict[str, Any]]:
        """Get transaction upload history."""
        return self.upload_manager.audit_logger.get_upload_history(entity_type='transactions')