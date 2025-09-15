"""
Bulk Payroll Processing with tax calculations, journal posting, and template management.
"""
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.upload_manager import UploadManager, ColumnMapping, UploadResult
from ..core.repositories import PayrollRunsRepository
from ..employees.manager import EmployeeManager
from ..tax.payroll import KenyanPayroll
from ..ledger.posting import LedgerPosting

class PayrollBulkProcessor:
    """Comprehensive payroll processing with bulk operations and journal integration."""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.repository = PayrollRunsRepository(tenant_id)
        self.upload_manager = UploadManager(tenant_id, 'payroll_lines')
        self.employee_manager = EmployeeManager(tenant_id)
        self.payroll_calculator = KenyanPayroll()
        self.ledger_posting = LedgerPosting(tenant_id)
    
    def get_template(self) -> pd.DataFrame:
        """Get payroll upload template."""
        return self.upload_manager.generate_template()
    
    def generate_payroll_template(self, payroll_period: str, employee_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """Generate payroll template pre-filled with employee data."""
        
        # Get employee payroll data
        employees = self.employee_manager.get_payroll_data(employee_ids)
        
        if not employees:
            return self.get_template()
        
        # Create template rows
        template_rows = []
        for emp in employees:
            template_rows.append({
                'employee_id': emp['employee_id'],
                'payroll_period': payroll_period,
                'gross_salary': emp['basic_salary'] + emp.get('house_allowance', 0) + emp.get('transport_allowance', 0) + emp.get('other_allowances', 0),
                'basic_salary': emp['basic_salary'],
                'house_allowance': emp.get('house_allowance', 0),
                'transport_allowance': emp.get('transport_allowance', 0),
                'other_allowances': emp.get('other_allowances', 0),
                'overtime_hours': 0.0,
                'overtime_rate': 0.0,
                'bonus': 0.0,
                'days_worked': 22,  # Default working days
                'days_in_month': 30  # Default days in month
            })
        
        return pd.DataFrame(template_rows)
    
    def bulk_process_payroll(
        self, 
        file_path: str,
        column_mappings: List[Dict[str, str]],
        payroll_period: str,
        auto_calculate: bool = True,
        auto_post_to_ledger: bool = False
    ) -> Dict[str, Any]:
        """
        Bulk process payroll with tax calculations and journal posting.
        
        Args:
            file_path: Path to CSV/Excel/JSON file
            column_mappings: List of {'source': 'col_name', 'target': 'payroll_field'}
            payroll_period: Payroll period (YYYY-MM format)
            auto_calculate: Whether to auto-calculate taxes and deductions
            auto_post_to_ledger: Whether to auto-post journal entries
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
        
        # Custom transformation for payroll data
        def transform_payroll_data(df: pd.DataFrame) -> pd.DataFrame:
            """Apply payroll-specific transformations and validations."""
            
            # Ensure payroll period is set
            df['payroll_period'] = payroll_period
            
            # Normalize employee IDs
            if 'employee_id' in df.columns:
                df['employee_id'] = df['employee_id'].str.strip().str.upper()
            
            # Ensure numeric fields are properly converted
            numeric_fields = ['gross_salary', 'basic_salary', 'house_allowance', 
                            'transport_allowance', 'other_allowances', 'overtime_hours',
                            'overtime_rate', 'bonus']
            for field in numeric_fields:
                if field in df.columns:
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)
            
            # Set defaults
            df['days_worked'] = pd.to_numeric(df.get('days_worked', 22), errors='coerce').fillna(22)
            df['days_in_month'] = pd.to_numeric(df.get('days_in_month', 30), errors='coerce').fillna(30)
            
            # Calculate gross salary if not provided
            if 'gross_salary' not in df.columns or df['gross_salary'].isna().any():
                df['gross_salary'] = (
                    df.get('basic_salary', 0) +
                    df.get('house_allowance', 0) +
                    df.get('transport_allowance', 0) +
                    df.get('other_allowances', 0) +
                    (df.get('overtime_hours', 0) * df.get('overtime_rate', 0)) +
                    df.get('bonus', 0)
                )
            
            # Pro-rate salary based on days worked
            df['prorated_gross'] = df['gross_salary'] * (df['days_worked'] / df['days_in_month'])
            
            return df
        
        # Process upload
        upload_result = self.upload_manager.process_upload(
            file_path=file_path,
            mappings=mappings,
            mode='upsert',  # Always upsert for payroll to handle corrections
            transform_fn=transform_payroll_data
        )
        
        if not upload_result.success:
            return {
                'success': False,
                'upload_result': upload_result.to_dict(),
                'payroll_calculations': None,
                'journal_posting_result': None
            }
        
        # Load staged data
        staging_file = self.upload_manager.staging_dir / f"{self.tenant_id}_payroll_lines_{upload_result.batch_id}.json"
        with open(staging_file, 'r') as f:
            import json
            staged_data = json.load(f)
        
        payroll_data = staged_data['data']
        
        # Calculate taxes and deductions if requested
        if auto_calculate:
            payroll_data = self._calculate_payroll_taxes(payroll_data)
        
        # Save payroll run to repository
        repo_result = self.repository.bulk_upsert(payroll_data, key_field='payroll_period')
        
        # Generate payroll summary
        payroll_summary = self._generate_payroll_summary(payroll_data, payroll_period)
        
        # Auto-post to ledger if requested
        journal_posting_result = None
        if auto_post_to_ledger:
            try:
                journal_posting_result = self._post_payroll_to_ledger(payroll_data, payroll_period)
            except Exception as e:
                journal_posting_result = {'error': str(e)}
        
        return {
            'success': True,
            'upload_result': upload_result.to_dict(),
            'repository_result': repo_result,
            'payroll_calculations': payroll_summary,
            'journal_posting_result': journal_posting_result,
            'payroll_period': payroll_period
        }
    
    def _calculate_payroll_taxes(self, payroll_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate Kenya taxes and deductions for each payroll line."""
        
        calculated_payroll = []
        
        for line in payroll_data:
            gross = float(line.get('prorated_gross', 0))
            
            if gross > 0:
                # Calculate Kenya taxes and deductions
                breakdown = self.payroll_calculator.payroll_breakdown(gross)
                
                # Add calculated fields to payroll line
                line.update({
                    'calculated_gross': breakdown['Gross'],
                    'paye_tax': breakdown['PAYE'],
                    'nssf_deduction': breakdown['NSSF'],
                    'nhif_deduction': breakdown['NHIF'],
                    'total_deductions': breakdown['PAYE'] + breakdown['NSSF'] + breakdown['NHIF'],
                    'net_pay': breakdown['Net'],
                    'calculation_date': datetime.now().isoformat()
                })
            else:
                # Zero gross salary
                line.update({
                    'calculated_gross': 0,
                    'paye_tax': 0,
                    'nssf_deduction': 0,
                    'nhif_deduction': 0,
                    'total_deductions': 0,
                    'net_pay': 0,
                    'calculation_date': datetime.now().isoformat()
                })
            
            calculated_payroll.append(line)
        
        return calculated_payroll
    
    def _generate_payroll_summary(self, payroll_data: List[Dict[str, Any]], period: str) -> Dict[str, Any]:
        """Generate comprehensive payroll summary."""
        
        if not payroll_data:
            return {'period': period, 'total_employees': 0}
        
        total_employees = len(payroll_data)
        total_gross = sum(float(line.get('calculated_gross', 0)) for line in payroll_data)
        total_paye = sum(float(line.get('paye_tax', 0)) for line in payroll_data)
        total_nssf = sum(float(line.get('nssf_deduction', 0)) for line in payroll_data)
        total_nhif = sum(float(line.get('nhif_deduction', 0)) for line in payroll_data)
        total_deductions = total_paye + total_nssf + total_nhif
        total_net = total_gross - total_deductions
        
        # Employee breakdown
        employee_details = []
        for line in payroll_data:
            employee_details.append({
                'employee_id': line.get('employee_id'),
                'gross': float(line.get('calculated_gross', 0)),
                'paye': float(line.get('paye_tax', 0)),
                'nssf': float(line.get('nssf_deduction', 0)),
                'nhif': float(line.get('nhif_deduction', 0)),
                'net': float(line.get('net_pay', 0))
            })
        
        return {
            'period': period,
            'total_employees': total_employees,
            'totals': {
                'gross': round(total_gross, 2),
                'paye': round(total_paye, 2),
                'nssf': round(total_nssf, 2),
                'nhif': round(total_nhif, 2),
                'deductions': round(total_deductions, 2),
                'net': round(total_net, 2)
            },
            'averages': {
                'gross': round(total_gross / total_employees, 2) if total_employees > 0 else 0,
                'net': round(total_net / total_employees, 2) if total_employees > 0 else 0
            },
            'employee_details': employee_details
        }
    
    def _post_payroll_to_ledger(self, payroll_data: List[Dict[str, Any]], period: str) -> Dict[str, Any]:
        """Post payroll journal entries to ledger."""
        
        # Calculate totals for journal entries
        total_gross = sum(float(line.get('calculated_gross', 0)) for line in payroll_data)
        total_paye = sum(float(line.get('paye_tax', 0)) for line in payroll_data)
        total_nssf = sum(float(line.get('nssf_deduction', 0)) for line in payroll_data)
        total_nhif = sum(float(line.get('nhif_deduction', 0)) for line in payroll_data)
        total_net = total_gross - total_paye - total_nssf - total_nhif
        
        entries_posted = 0
        
        try:
            # 1. Gross Salary Expense
            if total_gross > 0:
                self.ledger_posting.post_entry(
                    date=datetime.now().strftime('%Y-%m-%d'),
                    debit_acct='5100',  # Salaries Expense
                    credit_acct='2100',  # Accrued Salaries
                    amount=total_gross,
                    description=f'Payroll expense for {period}',
                    reference=f'PAYROLL-{period}'
                )
                entries_posted += 1
            
            # 2. PAYE Tax Liability
            if total_paye > 0:
                self.ledger_posting.post_entry(
                    date=datetime.now().strftime('%Y-%m-%d'),
                    debit_acct='2100',  # Accrued Salaries
                    credit_acct='2200',  # PAYE Tax Payable
                    amount=total_paye,
                    description=f'PAYE tax withholding for {period}',
                    reference=f'PAYE-{period}'
                )
                entries_posted += 1
            
            # 3. NSSF Liability
            if total_nssf > 0:
                self.ledger_posting.post_entry(
                    date=datetime.now().strftime('%Y-%m-%d'),
                    debit_acct='2100',  # Accrued Salaries
                    credit_acct='2300',  # NSSF Payable
                    amount=total_nssf,
                    description=f'NSSF deduction for {period}',
                    reference=f'NSSF-{period}'
                )
                entries_posted += 1
            
            # 4. NHIF Liability
            if total_nhif > 0:
                self.ledger_posting.post_entry(
                    date=datetime.now().strftime('%Y-%m-%d'),
                    debit_acct='2100',  # Accrued Salaries
                    credit_acct='2400',  # NHIF Payable
                    amount=total_nhif,
                    description=f'NHIF deduction for {period}',
                    reference=f'NHIF-{period}'
                )
                entries_posted += 1
            
            # 5. Net Pay (when actually paid)
            # Note: This would typically be posted separately when payment is made
            # self.ledger_posting.post_entry(
            #     date=datetime.now().strftime('%Y-%m-%d'),
            #     debit_acct='2100',  # Accrued Salaries
            #     credit_acct='1000',  # Cash
            #     amount=total_net,
            #     description=f'Net salary payment for {period}',
            #     reference=f'NETPAY-{period}'
            # )
            
            return {
                'entries_posted': entries_posted,
                'total_gross': total_gross,
                'total_paye': total_paye,
                'total_nssf': total_nssf,
                'total_nhif': total_nhif,
                'total_net': total_net,
                'success': True
            }
            
        except Exception as e:
            return {
                'entries_posted': entries_posted,
                'error': str(e),
                'success': False
            }
    
    def get_payroll_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent payroll runs."""
        runs = self.repository.load_data()
        
        # Sort by period (newest first)
        runs.sort(key=lambda x: x.get('payroll_period', ''), reverse=True)
        
        return runs[:limit]
    
    def get_payroll_run(self, period: str) -> Optional[Dict[str, Any]]:
        """Get specific payroll run by period."""
        return self.repository.get_run_by_period(period)
    
    def export_payroll(self, period: str, file_path: str) -> bool:
        """Export payroll run to Excel file."""
        run = self.get_payroll_run(period)
        
        if not run or not run.get('employees'):
            return False
        
        df = pd.DataFrame(run['employees'])
        df.to_excel(file_path, index=False)
        return True
    
    def get_upload_history(self) -> List[Dict[str, Any]]:
        """Get payroll upload history."""
        return self.upload_manager.audit_logger.get_upload_history(entity_type='payroll_lines')