"""
Employee Management with bulk upload, payroll integration, and master data management.
"""
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.upload_manager import UploadManager, ColumnMapping, UploadResult
from ..core.repositories import EmployeesRepository
from ..tax.payroll import KenyanPayroll

class EmployeeManager:
    """Comprehensive employee management with bulk operations and payroll integration."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.repository = EmployeesRepository(tenant_id)
        self.upload_manager = UploadManager(tenant_id, 'employees')
        self.payroll_calculator = KenyanPayroll()
    
    def get_template(self) -> pd.DataFrame:
        """Get employee upload template."""
        return self.upload_manager.generate_template()
    
    def bulk_upload(
        self, 
        file_path: str,
        column_mappings: List[Dict[str, str]],
        mode: str = 'upsert'
    ) -> Dict[str, Any]:
        """
        Bulk upload employees with validation and payroll setup.
        
        Args:
            file_path: Path to CSV/Excel/JSON file
            column_mappings: List of {'source': 'col_name', 'target': 'employee_field'}
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
        
        # Custom transformation for employee data
        def transform_employee_data(df: pd.DataFrame) -> pd.DataFrame:
            """Apply employee-specific transformations and validations."""
            
            # Standardize names
            if 'full_name' in df.columns:
                df['full_name'] = df['full_name'].str.strip().str.title()
            
            # Normalize employee IDs
            if 'employee_id' in df.columns:
                df['employee_id'] = df['employee_id'].str.strip().str.upper()
            
            # Auto-generate employee IDs if missing
            if 'employee_id' in df.columns:
                missing_ids = df['employee_id'].isna() | (df['employee_id'] == '')
                if missing_ids.any():
                    existing_employees = self.repository.load_data()
                    existing_ids = {emp.get('employee_id') for emp in existing_employees}
                    
                    counter = len(existing_employees) + 1
                    for idx in df[missing_ids].index:
                        while f"EMP{counter:03d}" in existing_ids:
                            counter += 1
                        new_id = f"EMP{counter:03d}"
                        df.loc[idx, 'employee_id'] = new_id
                        existing_ids.add(new_id)
                        counter += 1
            
            # Ensure numeric fields are properly converted
            numeric_fields = ['basic_salary', 'house_allowance', 'transport_allowance', 
                            'other_allowances', 'tax_relief']
            for field in numeric_fields:
                if field in df.columns:
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)
            
            # Set defaults
            df['is_active'] = df.get('is_active', True)
            df['tax_relief'] = df.get('tax_relief', 2400.0)  # Standard Kenya tax relief
            
            # Validate and format dates
            if 'hire_date' in df.columns:
                df['hire_date'] = pd.to_datetime(df['hire_date'], errors='coerce')
                df['hire_date'] = df['hire_date'].dt.strftime('%Y-%m-%d')
            
            # Calculate gross salary if not provided
            if 'basic_salary' in df.columns and 'gross_salary' not in df.columns:
                df['gross_salary'] = (
                    df.get('basic_salary', 0) +
                    df.get('house_allowance', 0) +
                    df.get('transport_allowance', 0) +
                    df.get('other_allowances', 0)
                )
            
            return df
        
        # Process upload
        upload_result = self.upload_manager.process_upload(
            file_path=file_path,
            mappings=mappings,
            mode=mode,
            transform_fn=transform_employee_data
        )
        
        if not upload_result.success:
            return {
                'success': False,
                'upload_result': upload_result.to_dict(),
                'employee_stats': None,
                'payroll_preview': None
            }
        
        # Load staged data and commit to repository
        staging_file = self.upload_manager.staging_dir / f"{self.tenant_id}_employees_{upload_result.batch_id}.json"
        with open(staging_file, 'r') as f:
            import json
            staged_data = json.load(f)
        
        employees_data = staged_data['data']
        
        # Bulk upsert to repository
        repo_result = self.repository.bulk_upsert(employees_data)
        
        # Generate payroll preview for uploaded employees
        payroll_preview = self._generate_payroll_preview(employees_data)
        
        return {
            'success': True,
            'upload_result': upload_result.to_dict(),
            'employee_stats': repo_result,
            'payroll_preview': payroll_preview,
            'total_employees': self.repository.get_count()
        }
    
    def _generate_payroll_preview(self, employees: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate payroll preview for uploaded employees."""
        
        if not employees:
            return {'total_employees': 0, 'total_gross': 0, 'total_deductions': 0, 'total_net': 0}
        
        total_gross = 0
        total_paye = 0
        total_nssf = 0
        total_nhif = 0
        total_net = 0
        
        payroll_details = []
        
        for emp in employees:
            gross = float(emp.get('gross_salary', 0))
            if gross <= 0:
                # Calculate from components
                gross = (
                    float(emp.get('basic_salary', 0)) +
                    float(emp.get('house_allowance', 0)) +
                    float(emp.get('transport_allowance', 0)) +
                    float(emp.get('other_allowances', 0))
                )
            
            if gross > 0:
                breakdown = self.payroll_calculator.payroll_breakdown(gross)
                
                total_gross += breakdown['Gross']
                total_paye += breakdown['PAYE']
                total_nssf += breakdown['NSSF']
                total_nhif += breakdown['NHIF']
                total_net += breakdown['Net']
                
                payroll_details.append({
                    'employee_id': emp.get('employee_id'),
                    'full_name': emp.get('full_name'),
                    'gross': breakdown['Gross'],
                    'paye': breakdown['PAYE'],
                    'nssf': breakdown['NSSF'],
                    'nhif': breakdown['NHIF'],
                    'net': breakdown['Net']
                })
        
        return {
            'total_employees': len(employees),
            'total_gross': round(total_gross, 2),
            'total_deductions': round(total_paye + total_nssf + total_nhif, 2),
            'total_paye': round(total_paye, 2),
            'total_nssf': round(total_nssf, 2),
            'total_nhif': round(total_nhif, 2),
            'total_net': round(total_net, 2),
            'details': payroll_details[:10]  # First 10 for preview
        }
    
    def get_employee_stats(self) -> Dict[str, Any]:
        """Get employee statistics and analytics."""
        employees = self.repository.load_data()
        
        if not employees:
            return {
                'total_employees': 0,
                'active_employees': 0,
                'by_department': {},
                'by_position': {},
                'salary_ranges': {},
                'average_salary': 0
            }
        
        active_employees = [e for e in employees if e.get('is_active', True)]
        
        # Department breakdown
        dept_counts = {}
        for emp in employees:
            dept = emp.get('department', 'Unknown')
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        # Position breakdown
        pos_counts = {}
        for emp in employees:
            pos = emp.get('position', 'Unknown')
            pos_counts[pos] = pos_counts.get(pos, 0) + 1
        
        # Salary analysis
        salaries = []
        for emp in active_employees:
            gross = emp.get('gross_salary') or (
                emp.get('basic_salary', 0) +
                emp.get('house_allowance', 0) +
                emp.get('transport_allowance', 0) +
                emp.get('other_allowances', 0)
            )
            if gross and gross > 0:
                salaries.append(gross)
        
        # Salary ranges
        salary_ranges = {
            '0-30K': len([s for s in salaries if s < 30000]),
            '30K-60K': len([s for s in salaries if 30000 <= s < 60000]),
            '60K-100K': len([s for s in salaries if 60000 <= s < 100000]),
            '100K+': len([s for s in salaries if s >= 100000])
        }
        
        avg_salary = sum(salaries) / len(salaries) if salaries else 0
        
        return {
            'total_employees': len(employees),
            'active_employees': len(active_employees),
            'by_department': dept_counts,
            'by_position': pos_counts,
            'salary_ranges': salary_ranges,
            'average_salary': round(avg_salary, 2)
        }
    
    def get_payroll_data(self, employee_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get employee data formatted for payroll processing."""
        return self.repository.get_payroll_data(employee_ids)
    
    def search_employees(self, query: str, active_only: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
        """Search employees by name, ID, or department."""
        employees = self.repository.load_data()
        
        if active_only:
            employees = [e for e in employees if e.get('is_active', True)]
        
        if not query:
            return employees[:limit]
        
        query_lower = query.lower().strip()
        matches = []
        
        for emp in employees:
            name = emp.get('full_name', '').lower()
            emp_id = emp.get('employee_id', '').lower()
            dept = emp.get('department', '').lower()
            pos = emp.get('position', '').lower()
            
            if (query_lower in name or 
                query_lower in emp_id or
                query_lower in dept or
                query_lower in pos or
                name.startswith(query_lower) or
                emp_id.startswith(query_lower)):
                matches.append(emp)
        
        return matches[:limit]
    
    def export_employees(self, file_path: str, active_only: bool = False) -> bool:
        """Export employees to Excel file."""
        employees = self.repository.load_data()
        
        if active_only:
            employees = [e for e in employees if e.get('is_active', True)]
        
        if not employees:
            return False
        
        return self.repository.export_to_excel(file_path)
    
    def get_upload_history(self) -> List[Dict[str, Any]]:
        """Get employee upload history."""
        return self.upload_manager.audit_logger.get_upload_history(entity_type='employees')