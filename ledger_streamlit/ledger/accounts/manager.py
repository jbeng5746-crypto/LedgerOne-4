"""
Chart of Accounts Management with bulk upload and tenant customization.
"""
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.upload_manager import UploadManager, ColumnMapping, UploadResult
from ..core.repositories import BaseRepository
from ..ledger.posting import CHART_OF_ACCOUNTS

class ChartOfAccountsRepository(BaseRepository):
    """Repository for chart of accounts data."""
    
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id, "chart_of_accounts")
    
    def bulk_upsert(self, records: List[Dict[str, Any]], key_field: str = "account_code") -> Dict[str, int]:
        """Bulk upsert accounts by account_code."""
        current_data = self.load_data()
        existing_map = {record.get(key_field): record for record in current_data}
        
        created = updated = 0
        
        for record in records:
            key_value = record.get(key_field)
            if not key_value:
                continue
                
            record['last_updated'] = datetime.now().isoformat()
            
            if key_value in existing_map:
                # Update existing
                existing_map[key_value].update(record)
                updated += 1
            else:
                # Create new
                record['created_at'] = datetime.now().isoformat()
                existing_map[key_value] = record
                created += 1
        
        # Save updated data
        updated_data = list(existing_map.values())
        self.save_data(updated_data)
        
        return {"created": created, "updated": updated, "total": len(updated_data)}
    
    def find_by_key(self, key_field: str, key_value: Any) -> Optional[Dict[str, Any]]:
        """Find account by key field."""
        data = self.load_data()
        for record in data:
            if record.get(key_field) == key_value:
                return record
        return None

class ChartOfAccountsManager:
    """Chart of Accounts management with bulk operations and tenant customization."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.repository = ChartOfAccountsRepository(tenant_id)
        self.upload_manager = UploadManager(tenant_id, 'chart_of_accounts')
    
    def get_template(self) -> pd.DataFrame:
        """Get chart of accounts upload template."""
        # Start with system default accounts
        default_accounts = []
        for code, name in CHART_OF_ACCOUNTS.items():
            account_type = self._determine_account_type(code)
            default_accounts.append({
                'account_code': code,
                'account_name': name,
                'account_type': account_type,
                'parent_code': '',
                'is_active': True,
                'description': f'Default {account_type} account'
            })
        
        template_df = pd.DataFrame(default_accounts)
        return template_df
    
    def _determine_account_type(self, account_code: str) -> str:
        """Determine account type from account code."""
        if account_code.startswith('1'):
            return 'asset'
        elif account_code.startswith('2'):
            return 'liability'  
        elif account_code.startswith('3'):
            return 'equity'
        elif account_code.startswith('4'):
            return 'revenue'
        elif account_code.startswith('5'):
            return 'expense'
        else:
            return 'other'
    
    def bulk_upload(
        self, 
        file_path: str,
        column_mappings: List[Dict[str, str]],
        mode: str = 'upsert'
    ) -> Dict[str, Any]:
        """
        Bulk upload chart of accounts with validation and tenant customization.
        
        Args:
            file_path: Path to CSV/Excel/JSON file
            column_mappings: List of {'source': 'col_name', 'target': 'account_field'}
            mode: 'append', 'upsert', or 'replace'
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
        
        # Custom transformation for chart of accounts data
        def transform_accounts_data(df: pd.DataFrame) -> pd.DataFrame:
            """Apply account-specific transformations."""
            
            # Standardize account codes
            if 'account_code' in df.columns:
                df['account_code'] = df['account_code'].astype(str).str.strip()
            
            # Standardize account names
            if 'account_name' in df.columns:
                df['account_name'] = df['account_name'].str.strip().str.title()
            
            # Auto-determine account type if not provided
            if 'account_type' not in df.columns or df['account_type'].isna().any():
                for idx, row in df.iterrows():
                    if pd.isna(row.get('account_type')) and row.get('account_code'):
                        df.loc[idx, 'account_type'] = self._determine_account_type(str(row['account_code']))
            
            # Set defaults
            df['is_active'] = df.get('is_active', True)
            
            return df
        
        # Process upload
        upload_result = self.upload_manager.process_upload(
            file_path=file_path,
            mappings=mappings,
            mode=mode,
            transform_fn=transform_accounts_data
        )
        
        if not upload_result.success:
            return {
                'success': False,
                'upload_result': upload_result.to_dict(),
                'accounts_stats': None
            }
        
        # Load staged data and commit to repository
        staging_file = self.upload_manager.staging_dir / f"{self.tenant_id}_chart_of_accounts_{upload_result.batch_id}.json"
        with open(staging_file, 'r') as f:
            import json
            staged_data = json.load(f)
        
        accounts_data = staged_data['data']
        
        # Bulk upsert to repository
        repo_result = self.repository.bulk_upsert(accounts_data)
        
        return {
            'success': True,
            'upload_result': upload_result.to_dict(),
            'accounts_stats': repo_result,
            'total_accounts': self.repository.get_count()
        }
    
    def get_account_stats(self) -> Dict[str, Any]:
        """Get chart of accounts statistics."""
        accounts = self.repository.load_data()
        
        if not accounts:
            return {
                'total_accounts': 0,
                'active_accounts': 0,
                'by_type': {},
                'custom_accounts': 0
            }
        
        active_accounts = [a for a in accounts if a.get('is_active', True)]
        
        # Type breakdown
        type_counts = {}
        for account in accounts:
            acc_type = account.get('account_type', 'unknown')
            type_counts[acc_type] = type_counts.get(acc_type, 0) + 1
        
        # Count custom accounts (not in default chart)
        custom_count = len([a for a in accounts if a.get('account_code') not in CHART_OF_ACCOUNTS])
        
        return {
            'total_accounts': len(accounts),
            'active_accounts': len(active_accounts),
            'by_type': type_counts,
            'custom_accounts': custom_count
        }
    
    def export_accounts(self, file_path: str, active_only: bool = False) -> bool:
        """Export chart of accounts to Excel file."""
        accounts = self.repository.load_data()
        
        if active_only:
            accounts = [a for a in accounts if a.get('is_active', True)]
        
        if not accounts:
            return False
        
        return self.repository.export_to_excel(file_path)
    
    def get_upload_history(self) -> List[Dict[str, Any]]:
        """Get chart of accounts upload history."""
        return self.upload_manager.audit_logger.get_upload_history(entity_type='chart_of_accounts')