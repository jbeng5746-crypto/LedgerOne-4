"""
Repository layer for data persistence with bulk operations and audit trails.
Provides consistent interface for all entity data management.
"""
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from abc import ABC, abstractmethod

class BaseRepository(ABC):
    """Base repository with common data persistence patterns."""
    
    def __init__(self, tenant_id: str, entity_type: str):
        self.tenant_id = tenant_id
        self.entity_type = entity_type
        
        # Setup directory structure
        self.data_dir = Path(__file__).resolve().parents[2] / "data" 
        self.entity_dir = self.data_dir / entity_type
        self.archive_dir = self.entity_dir / "archive"
        
        for dir_path in [self.entity_dir, self.archive_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _get_data_file(self) -> Path:
        """Get main data file path for tenant."""
        return self.entity_dir / f"{self.tenant_id}_{self.entity_type}.json"
    
    def _get_archive_file(self) -> Path:
        """Get archive file path with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.archive_dir / f"{self.tenant_id}_{self.entity_type}_{timestamp}.json"
    
    def load_data(self) -> List[Dict[str, Any]]:
        """Load current data from JSON file."""
        data_file = self._get_data_file()
        if not data_file.exists():
            return []
        
        try:
            with open(data_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def save_data(self, data: List[Dict[str, Any]], create_backup: bool = True) -> bool:
        """Save data to JSON file with optional backup."""
        try:
            # Create backup if requested and data exists
            if create_backup and self._get_data_file().exists():
                self._create_backup()
            
            # Save new data
            data_file = self._get_data_file()
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            print(f"Error saving data: {e}")
            return False
    
    def _create_backup(self) -> bool:
        """Create timestamped backup of current data."""
        try:
            current_data = self.load_data()
            if current_data:
                archive_file = self._get_archive_file()
                with open(archive_file, 'w') as f:
                    json.dump(current_data, f, indent=2, default=str)
            return True
        except Exception:
            return False
    
    def export_to_excel(self, file_path: Union[str, Path]) -> bool:
        """Export current data to Excel file."""
        try:
            data = self.load_data()
            if not data:
                return False
            
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False)
            return True
            
        except Exception:
            return False
    
    def get_count(self) -> int:
        """Get total record count."""
        return len(self.load_data())
    
    @abstractmethod
    def bulk_upsert(self, records: List[Dict[str, Any]], key_field: str) -> Dict[str, int]:
        """Bulk upsert records. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def find_by_key(self, key_field: str, key_value: Any) -> Optional[Dict[str, Any]]:
        """Find single record by key field. Must be implemented by subclasses."""
        pass

class VendorsRepository(BaseRepository):
    """Repository for vendor master data."""
    
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id, "vendors")
    
    def bulk_upsert(self, records: List[Dict[str, Any]], key_field: str = "vendor_code") -> Dict[str, int]:
        """Bulk upsert vendors by vendor_code."""
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
        """Find vendor by key field."""
        data = self.load_data()
        for record in data:
            if record.get(key_field) == key_value:
                return record
        return None
    
    def search_by_name(self, name_pattern: str) -> List[Dict[str, Any]]:
        """Search vendors by name pattern."""
        data = self.load_data()
        pattern = name_pattern.lower()
        return [
            record for record in data 
            if pattern in record.get('vendor_name', '').lower()
        ]
    
    def get_active_vendors(self) -> List[Dict[str, Any]]:
        """Get all active vendors."""
        data = self.load_data()
        return [record for record in data if record.get('is_active', True)]

class EmployeesRepository(BaseRepository):
    """Repository for employee master data."""
    
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id, "employees")
    
    def bulk_upsert(self, records: List[Dict[str, Any]], key_field: str = "employee_id") -> Dict[str, int]:
        """Bulk upsert employees by employee_id."""
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
        """Find employee by key field."""
        data = self.load_data()
        for record in data:
            if record.get(key_field) == key_value:
                return record
        return None
    
    def get_active_employees(self) -> List[Dict[str, Any]]:
        """Get all active employees."""
        data = self.load_data()
        return [record for record in data if record.get('is_active', True)]
    
    def get_payroll_data(self, employee_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get employee data for payroll processing."""
        employees = self.get_active_employees()
        
        if employee_ids:
            employees = [emp for emp in employees if emp.get('employee_id') in employee_ids]
        
        # Return payroll-relevant fields
        payroll_data = []
        for emp in employees:
            payroll_data.append({
                'employee_id': emp.get('employee_id'),
                'full_name': emp.get('full_name'), 
                'basic_salary': emp.get('basic_salary', 0),
                'house_allowance': emp.get('house_allowance', 0),
                'transport_allowance': emp.get('transport_allowance', 0),
                'other_allowances': emp.get('other_allowances', 0),
                'kra_pin': emp.get('kra_pin'),
                'nssf_number': emp.get('nssf_number'),
                'nhif_number': emp.get('nhif_number'),
                'bank_name': emp.get('bank_name'),
                'bank_account': emp.get('bank_account'),
                'tax_relief': emp.get('tax_relief', 2400)
            })
        
        return payroll_data

class TransactionsRepository(BaseRepository):
    """Repository for transaction data."""
    
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id, "transactions")
    
    def bulk_upsert(self, records: List[Dict[str, Any]], key_field: str = "transaction_id") -> Dict[str, int]:
        """Bulk upsert transactions by transaction_id."""
        current_data = self.load_data()
        existing_map = {record.get(key_field): record for record in current_data if record.get(key_field)}
        
        created = updated = 0
        
        for record in records:
            key_value = record.get(key_field)
            
            # Generate transaction_id if not provided
            if not key_value:
                from uuid import uuid4
                key_value = f"TXN_{datetime.now().strftime('%Y%m%d')}_{str(uuid4())[:8]}"
                record[key_field] = key_value
                
            record['last_updated'] = datetime.now().isoformat()
            
            if key_value in existing_map:
                # Update existing
                existing_map[key_value].update(record)
                updated += 1
            else:
                # Create new
                record['created_at'] = datetime.now().isoformat()
                record['status'] = record.get('status', 'pending')
                existing_map[key_value] = record
                created += 1
        
        # Save updated data
        updated_data = list(existing_map.values())
        self.save_data(updated_data)
        
        return {"created": created, "updated": updated, "total": len(updated_data)}
    
    def find_by_key(self, key_field: str, key_value: Any) -> Optional[Dict[str, Any]]:
        """Find transaction by key field."""
        data = self.load_data()
        for record in data:
            if record.get(key_field) == key_value:
                return record
        return None
    
    def get_pending_transactions(self) -> List[Dict[str, Any]]:
        """Get all pending transactions."""
        data = self.load_data()
        return [record for record in data if record.get('status') == 'pending']
    
    def get_transactions_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get transactions within date range."""
        data = self.load_data()
        return [
            record for record in data 
            if start_date <= record.get('date', '') <= end_date
        ]

class PayrollRunsRepository(BaseRepository):
    """Repository for payroll run data."""
    
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id, "payroll_runs")
    
    def bulk_upsert(self, records: List[Dict[str, Any]], key_field: str = "payroll_period") -> Dict[str, int]:
        """Bulk upsert payroll runs by period."""
        current_data = self.load_data()
        
        # Group by payroll period
        existing_runs = {}
        for record in current_data:
            period = record.get('payroll_period')
            if period:
                if period not in existing_runs:
                    existing_runs[period] = {'payroll_period': period, 'employees': []}
                existing_runs[period]['employees'].extend(record.get('employees', []))
        
        created = updated = 0
        
        # Process new records
        new_runs = {}
        for record in records:
            period = record.get('payroll_period')
            if not period:
                continue
                
            if period not in new_runs:
                new_runs[period] = {
                    'payroll_period': period,
                    'employees': [],
                    'status': 'pending',
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
            
            new_runs[period]['employees'].append(record)
        
        # Merge with existing data
        for period, run_data in new_runs.items():
            if period in existing_runs:
                # Update existing run
                existing_runs[period]['employees'] = run_data['employees']
                existing_runs[period]['last_updated'] = datetime.now().isoformat()
                updated += 1
            else:
                # Create new run
                existing_runs[period] = run_data
                created += 1
        
        # Save updated data
        updated_data = list(existing_runs.values())
        self.save_data(updated_data)
        
        return {"created": created, "updated": updated, "total": len(updated_data)}
    
    def find_by_key(self, key_field: str, key_value: Any) -> Optional[Dict[str, Any]]:
        """Find payroll run by key field."""
        data = self.load_data()
        for record in data:
            if record.get(key_field) == key_value:
                return record
        return None
    
    def get_run_by_period(self, period: str) -> Optional[Dict[str, Any]]:
        """Get payroll run by period (YYYY-MM)."""
        return self.find_by_key('payroll_period', period)