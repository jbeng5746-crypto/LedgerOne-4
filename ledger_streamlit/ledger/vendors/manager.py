"""
Vendor Management with bulk upload, deduplication, and master data management.
Integrates with VendorNormalizer for smart vendor matching.
"""
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.upload_manager import UploadManager, ColumnMapping, UploadResult
from ..core.repositories import VendorsRepository
from ..ml.vendor_normalizer import VendorNormalizer

class VendorManager:
    """Comprehensive vendor management with bulk operations."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.repository = VendorsRepository(tenant_id)
        self.upload_manager = UploadManager(tenant_id, 'vendors')
        self.normalizer = VendorNormalizer(tenant_id)
        
        # Load existing normalizer model if available
        try:
            self.normalizer.load()
        except:
            # No existing model, will train on first upload
            pass
    
    def get_template(self) -> pd.DataFrame:
        """Get vendor upload template."""
        return self.upload_manager.generate_template()
    
    def bulk_upload(
        self, 
        file_path: str,
        column_mappings: List[Dict[str, str]],
        mode: str = 'upsert',
        auto_deduplicate: bool = True
    ) -> Dict[str, Any]:
        """
        Bulk upload vendors with deduplication and normalization.
        
        Args:
            file_path: Path to CSV/Excel/JSON file
            column_mappings: List of {'source': 'col_name', 'target': 'vendor_field'}
            mode: 'append', 'upsert', or 'replace'
            auto_deduplicate: Whether to auto-deduplicate similar vendor names
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
        
        # Custom transformation for vendor data
        def transform_vendor_data(df: pd.DataFrame) -> pd.DataFrame:
            """Apply vendor-specific transformations."""
            
            # Standardize vendor names
            if 'vendor_name' in df.columns:
                df['vendor_name'] = df['vendor_name'].str.strip().str.title()
            
            # Normalize vendor codes
            if 'vendor_code' in df.columns:
                df['vendor_code'] = df['vendor_code'].str.strip().str.upper()
            
            # Set defaults
            df['is_active'] = df.get('is_active', True)
            df['tax_status'] = df.get('tax_status', 'unknown')
            df['payment_terms'] = pd.to_numeric(df.get('payment_terms', 30), errors='coerce').fillna(30)
            df['credit_limit'] = pd.to_numeric(df.get('credit_limit', 0), errors='coerce').fillna(0)
            
            # Auto-generate vendor codes if missing
            if 'vendor_code' in df.columns:
                missing_codes = df['vendor_code'].isna() | (df['vendor_code'] == '')
                if missing_codes.any():
                    for idx in df[missing_codes].index:
                        vendor_name = df.loc[idx, 'vendor_name']
                        if vendor_name:
                            # Generate code from name: first 3 chars + 3 digits
                            base_code = ''.join(c for c in vendor_name.upper()[:3] if c.isalpha())
                            counter = 1
                            while True:
                                code = f"{base_code}{counter:03d}"
                                if not self.repository.find_by_key('vendor_code', code):
                                    df.loc[idx, 'vendor_code'] = code
                                    break
                                counter += 1
            
            return df
        
        # Process upload
        upload_result = self.upload_manager.process_upload(
            file_path=file_path,
            mappings=mappings,
            mode=mode,
            transform_fn=transform_vendor_data
        )
        
        if not upload_result.success:
            return {
                'success': False,
                'upload_result': upload_result.to_dict(),
                'vendor_stats': None,
                'deduplication_report': None
            }
        
        # Load staged data and commit to repository
        staging_file = self.upload_manager.staging_dir / f"{self.tenant_id}_vendors_{upload_result.batch_id}.json"
        with open(staging_file, 'r') as f:
            import json
            staged_data = json.load(f)
        
        vendors_data = staged_data['data']
        
        # Apply deduplication if requested
        deduplication_report = None
        if auto_deduplicate and vendors_data:
            vendors_data, deduplication_report = self._deduplicate_vendors(vendors_data)
        
        # Bulk upsert to repository
        repo_result = self.repository.bulk_upsert(vendors_data)
        
        # Update vendor normalizer with new data
        self._update_normalizer(vendors_data)
        
        return {
            'success': True,
            'upload_result': upload_result.to_dict(),
            'vendor_stats': repo_result,
            'deduplication_report': deduplication_report,
            'total_vendors': self.repository.get_count()
        }
    
    def _deduplicate_vendors(self, vendors: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Deduplicate vendors by finding similar names and merging data.
        Returns (deduplicated_vendors, report).
        """
        
        if not vendors:
            return vendors, {'duplicates_found': 0, 'duplicates_merged': 0}
        
        # Load existing vendors for comparison
        existing_vendors = self.repository.load_data()
        all_vendor_names = [v.get('vendor_name', '') for v in existing_vendors]
        
        duplicates_found = 0
        duplicates_merged = 0
        deduplicated = []
        processed_names = set()
        
        for vendor in vendors:
            vendor_name = vendor.get('vendor_name', '').strip()
            
            if not vendor_name or vendor_name in processed_names:
                continue
            
            # Check for similar names in existing data
            if self.normalizer.vectorizer and all_vendor_names:
                try:
                    norm_result = self.normalizer.normalize(vendor_name, fuzzy_threshold=85)
                    canonical_name = norm_result.get('canonical')
                    similarity_score = norm_result.get('score', 0)
                    
                    if canonical_name and similarity_score > 85:
                        # Found potential duplicate
                        duplicates_found += 1
                        
                        # Find existing vendor record
                        existing_vendor = next(
                            (v for v in existing_vendors if v.get('vendor_name') == canonical_name),
                            None
                        )
                        
                        if existing_vendor:
                            # Merge data (new data takes precedence for non-empty fields)
                            merged_vendor = existing_vendor.copy()
                            for key, value in vendor.items():
                                if value and str(value).strip():
                                    merged_vendor[key] = value
                            
                            merged_vendor['last_updated'] = datetime.now().isoformat()
                            deduplicated.append(merged_vendor)
                            duplicates_merged += 1
                        else:
                            deduplicated.append(vendor)
                    else:
                        deduplicated.append(vendor)
                        
                except Exception:
                    # If normalization fails, add vendor as-is
                    deduplicated.append(vendor)
            else:
                deduplicated.append(vendor)
            
            processed_names.add(vendor_name)
        
        return deduplicated, {
            'duplicates_found': duplicates_found,
            'duplicates_merged': duplicates_merged,
            'total_processed': len(vendors),
            'final_count': len(deduplicated)
        }
    
    def _update_normalizer(self, vendors: List[Dict[str, Any]]):
        """Update vendor normalizer with new vendor names."""
        
        # Get all vendor names (existing + new)
        existing_vendors = self.repository.load_data()
        all_vendor_names = []
        
        for vendor in existing_vendors + vendors:
            name = vendor.get('vendor_name')
            if name and name.strip():
                all_vendor_names.append(name.strip())
        
        # Remove duplicates while preserving order
        unique_names = list(dict.fromkeys(all_vendor_names))
        
        if len(unique_names) >= 3:  # Need minimum vendors to train
            try:
                self.normalizer.train(unique_names)
                self.normalizer.save()
            except Exception as e:
                print(f"Warning: Could not update vendor normalizer: {e}")
    
    def search_vendors(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search vendors by name or code."""
        vendors = self.repository.load_data()
        
        if not query:
            return vendors[:limit]
        
        query_lower = query.lower().strip()
        matches = []
        
        for vendor in vendors:
            name = vendor.get('vendor_name', '').lower()
            code = vendor.get('vendor_code', '').lower()
            
            if (query_lower in name or 
                query_lower in code or
                name.startswith(query_lower) or
                code.startswith(query_lower)):
                matches.append(vendor)
        
        return matches[:limit]
    
    def get_vendor_stats(self) -> Dict[str, Any]:
        """Get vendor statistics and analytics."""
        vendors = self.repository.load_data()
        
        if not vendors:
            return {
                'total_vendors': 0,
                'active_vendors': 0,
                'by_tax_status': {},
                'by_category': {},
                'average_credit_limit': 0,
                'average_payment_terms': 0
            }
        
        active_vendors = [v for v in vendors if v.get('is_active', True)]
        
        # Tax status breakdown
        tax_status_counts = {}
        for vendor in vendors:
            status = vendor.get('tax_status', 'unknown')
            tax_status_counts[status] = tax_status_counts.get(status, 0) + 1
        
        # Category breakdown
        category_counts = {}
        for vendor in vendors:
            category = vendor.get('category', 'uncategorized')
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Financial metrics
        credit_limits = [v.get('credit_limit', 0) for v in vendors if v.get('credit_limit')]
        payment_terms = [v.get('payment_terms', 0) for v in vendors if v.get('payment_terms')]
        
        avg_credit_limit = sum(credit_limits) / len(credit_limits) if credit_limits else 0
        avg_payment_terms = sum(payment_terms) / len(payment_terms) if payment_terms else 0
        
        return {
            'total_vendors': len(vendors),
            'active_vendors': len(active_vendors),
            'by_tax_status': tax_status_counts,
            'by_category': category_counts,
            'average_credit_limit': round(avg_credit_limit, 2),
            'average_payment_terms': round(avg_payment_terms, 1)
        }
    
    def export_vendors(self, file_path: str, active_only: bool = False) -> bool:
        """Export vendors to Excel file."""
        vendors = self.repository.load_data()
        
        if active_only:
            vendors = [v for v in vendors if v.get('is_active', True)]
        
        if not vendors:
            return False
        
        return self.repository.export_to_excel(file_path)
    
    def get_upload_history(self) -> List[Dict[str, Any]]:
        """Get vendor upload history."""
        return self.upload_manager.audit_logger.get_upload_history(entity_type='vendors')