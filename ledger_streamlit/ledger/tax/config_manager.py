"""
Tax Configuration Management with bulk upload and versioning.
"""
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.upload_manager import UploadManager, ColumnMapping, UploadResult
from ..core.repositories import BaseRepository

class TaxConfigRepository(BaseRepository):
    """Repository for tax configuration data with versioning."""
    
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id, "tax_configs")
    
    def bulk_upsert(self, records: List[Dict[str, Any]], key_field: str = "config_key") -> Dict[str, int]:
        """Bulk upsert tax configs with versioning."""
        current_data = self.load_data()
        
        # Group existing by config_key
        existing_map = {}
        for record in current_data:
            key = record.get(key_field)
            if key:
                if key not in existing_map:
                    existing_map[key] = []
                existing_map[key].append(record)
        
        created = updated = 0
        new_configs = []
        
        for record in records:
            key_value = record.get(key_field)
            if not key_value:
                continue
            
            record['last_updated'] = datetime.now().isoformat()
            effective_date = record.get('effective_date', datetime.now().strftime('%Y-%m-%d'))
            
            # Check if this exact config already exists
            existing_configs = existing_map.get(key_value, [])
            existing_config = None
            
            for config in existing_configs:
                if config.get('effective_date') == effective_date:
                    existing_config = config
                    break
            
            if existing_config:
                # Update existing config
                existing_config.update(record)
                updated += 1
            else:
                # Create new version
                record['created_at'] = datetime.now().isoformat()
                record['version'] = len(existing_configs) + 1
                new_configs.append(record)
                created += 1
        
        # Combine existing and new configs
        all_configs = []
        for configs_list in existing_map.values():
            all_configs.extend(configs_list)
        all_configs.extend(new_configs)
        
        # Save updated data
        self.save_data(all_configs)
        
        return {"created": created, "updated": updated, "total": len(all_configs)}
    
    def find_by_key(self, key_field: str, key_value: Any, effective_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find tax config by key field and effective date."""
        data = self.load_data()
        configs = [r for r in data if r.get(key_field) == key_value]
        
        if not configs:
            return None
        
        if effective_date:
            # Find config effective for specific date
            valid_configs = [c for c in configs if c.get('effective_date', '') <= effective_date]
            if valid_configs:
                return max(valid_configs, key=lambda x: x.get('effective_date', ''))
        
        # Return latest config
        return max(configs, key=lambda x: x.get('effective_date', ''))

class TaxConfigManager:
    """Tax configuration management with bulk operations and versioning."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.repository = TaxConfigRepository(tenant_id)
        self.upload_manager = UploadManager(tenant_id, 'tax_configs')
    
    def get_template(self) -> pd.DataFrame:
        """Get tax configuration upload template."""
        # Create template with common Kenya tax configurations
        default_configs = [
            {
                'config_key': 'vat_rate',
                'config_value': '0.16',
                'effective_date': '2024-01-01',
                'description': 'Standard VAT rate for Kenya',
                'is_active': True
            },
            {
                'config_key': 'paye_relief',
                'config_value': '2400.00',
                'effective_date': '2024-01-01', 
                'description': 'Monthly PAYE tax relief amount',
                'is_active': True
            },
            {
                'config_key': 'nssf_rate',
                'config_value': '0.06',
                'effective_date': '2024-01-01',
                'description': 'NSSF contribution rate (employee + employer)',
                'is_active': True
            }
        ]
        
        return pd.DataFrame(default_configs)
    
    def bulk_upload(
        self, 
        file_path: str,
        column_mappings: List[Dict[str, str]],
        mode: str = 'upsert'
    ) -> Dict[str, Any]:
        """
        Bulk upload tax configurations with versioning.
        
        Args:
            file_path: Path to CSV/Excel/JSON file
            column_mappings: List of {'source': 'col_name', 'target': 'config_field'}
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
        
        # Custom transformation for tax config data
        def transform_tax_config_data(df: pd.DataFrame) -> pd.DataFrame:
            """Apply tax config-specific transformations."""
            
            # Standardize config keys
            if 'config_key' in df.columns:
                df['config_key'] = df['config_key'].str.strip().str.lower()
            
            # Ensure effective dates are properly formatted
            if 'effective_date' in df.columns:
                df['effective_date'] = pd.to_datetime(df['effective_date'], errors='coerce')
                df['effective_date'] = df['effective_date'].dt.strftime('%Y-%m-%d')
            else:
                df['effective_date'] = datetime.now().strftime('%Y-%m-%d')
            
            # Set defaults
            df['is_active'] = df.get('is_active', True)
            
            return df
        
        # Process upload
        upload_result = self.upload_manager.process_upload(
            file_path=file_path,
            mappings=mappings,
            mode=mode,
            transform_fn=transform_tax_config_data
        )
        
        if not upload_result.success:
            return {
                'success': False,
                'upload_result': upload_result.to_dict(),
                'config_stats': None
            }
        
        # Load staged data and commit to repository
        staging_file = self.upload_manager.staging_dir / f"{self.tenant_id}_tax_configs_{upload_result.batch_id}.json"
        with open(staging_file, 'r') as f:
            import json
            staged_data = json.load(f)
        
        configs_data = staged_data['data']
        
        # Bulk upsert to repository
        repo_result = self.repository.bulk_upsert(configs_data)
        
        return {
            'success': True,
            'upload_result': upload_result.to_dict(),
            'config_stats': repo_result,
            'total_configs': self.repository.get_count()
        }
    
    def get_config_stats(self) -> Dict[str, Any]:
        """Get tax configuration statistics."""
        configs = self.repository.load_data()
        
        if not configs:
            return {
                'total_configs': 0,
                'active_configs': 0,
                'by_key': {},
                'latest_version': {}
            }
        
        active_configs = [c for c in configs if c.get('is_active', True)]
        
        # Group by config key
        by_key = {}
        latest_version = {}
        
        for config in configs:
            key = config.get('config_key', 'unknown')
            by_key[key] = by_key.get(key, 0) + 1
            
            # Track latest version
            if key not in latest_version or config.get('effective_date', '') > latest_version[key].get('effective_date', ''):
                latest_version[key] = config
        
        return {
            'total_configs': len(configs),
            'active_configs': len(active_configs),
            'by_key': by_key,
            'latest_version': latest_version,
            'unique_keys': len(by_key)
        }
    
    def get_active_config(self, config_key: str, effective_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get active configuration for a specific key and date."""
        if not effective_date:
            effective_date = datetime.now().strftime('%Y-%m-%d')
        
        return self.repository.find_by_key('config_key', config_key, effective_date)
    
    def export_configs(self, file_path: str, active_only: bool = False) -> bool:
        """Export tax configurations to Excel file."""
        configs = self.repository.load_data()
        
        if active_only:
            configs = [c for c in configs if c.get('is_active', True)]
        
        if not configs:
            return False
        
        return self.repository.export_to_excel(file_path)
    
    def get_upload_history(self) -> List[Dict[str, Any]]:
        """Get tax configuration upload history."""
        return self.upload_manager.audit_logger.get_upload_history(entity_type='tax_configs')