"""
Schema Registry for all entity types with JSON Schema validation.
Provides consistent data validation across upload processes.
"""
from typing import Dict, Any

class SchemaRegistry:
    """Registry of JSON schemas for all uploadable entity types."""
    
    def __init__(self):
        self.schemas = self._initialize_schemas()
    
    def get_schema(self, entity_type: str) -> Dict[str, Any]:
        """Get schema for entity type."""
        if entity_type not in self.schemas:
            raise ValueError(f"Schema not found for entity type: {entity_type}")
        return self.schemas[entity_type]
    
    def get_available_entities(self) -> list[str]:
        """Get list of all available entity types."""
        return list(self.schemas.keys())
    
    def _initialize_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Initialize all schema definitions."""
        return {
            'vendors': self._vendor_schema(),
            'employees': self._employee_schema(), 
            'transactions': self._transaction_schema(),
            'payroll_lines': self._payroll_line_schema(),
            'chart_of_accounts': self._chart_of_accounts_schema(),
            'tax_configs': self._tax_config_schema(),
            'approvals': self._approval_schema()
        }
    
    def _vendor_schema(self) -> Dict[str, Any]:
        """Schema for vendor master data."""
        return {
            "type": "object",
            "required": ["vendor_name", "vendor_code"],
            "properties": {
                "vendor_code": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 20,
                    "example": "VEN001"
                },
                "vendor_name": {
                    "type": "string", 
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "Acme Supplies Ltd"
                },
                "kra_pin": {
                    "type": "string",
                    "pattern": "^[A-Z0-9]{11}$",
                    "example": "P051234567M"
                },
                "email": {
                    "type": "string",
                    "format": "email",
                    "example": "accounts@acme.co.ke"
                },
                "phone": {
                    "type": "string",
                    "maxLength": 20,
                    "example": "+254701234567"
                },
                "payment_terms": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 365,
                    "example": 30
                },
                "credit_limit": {
                    "type": "number",
                    "minimum": 0,
                    "example": 100000.00
                },
                "bank_name": {
                    "type": "string",
                    "maxLength": 50,
                    "example": "KCB Bank"
                },
                "bank_account": {
                    "type": "string",
                    "maxLength": 30,
                    "example": "1234567890"
                },
                "address": {
                    "type": "string",
                    "maxLength": 200,
                    "example": "P.O. Box 12345, Nairobi"
                },
                "contact_person": {
                    "type": "string",
                    "maxLength": 50,
                    "example": "John Doe"
                },
                "tax_status": {
                    "type": "string",
                    "enum": ["vat_registered", "vat_exempt", "unknown"],
                    "example": "vat_registered"
                },
                "is_active": {
                    "type": "boolean",
                    "example": True
                },
                "category": {
                    "type": "string",
                    "maxLength": 30,
                    "example": "Office Supplies"
                }
            }
        }
    
    def _employee_schema(self) -> Dict[str, Any]:
        """Schema for employee master data."""
        return {
            "type": "object", 
            "required": ["employee_id", "full_name", "basic_salary"],
            "properties": {
                "employee_id": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 20,
                    "example": "EMP001"
                },
                "full_name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "Jane Wanjiku Kamau"
                },
                "email": {
                    "type": "string",
                    "format": "email",
                    "example": "jane.kamau@company.co.ke"
                },
                "phone": {
                    "type": "string",
                    "maxLength": 20,
                    "example": "+254701234567"
                },
                "national_id": {
                    "type": "string",
                    "pattern": "^[0-9]{8}$",
                    "example": "12345678"
                },
                "kra_pin": {
                    "type": "string",
                    "pattern": "^[A-Z0-9]{11}$",
                    "example": "A012345678Z"
                },
                "nssf_number": {
                    "type": "string",
                    "maxLength": 20,
                    "example": "NSSF12345"
                },
                "nhif_number": {
                    "type": "string",
                    "maxLength": 20,
                    "example": "NHIF12345"
                },
                "basic_salary": {
                    "type": "number",
                    "minimum": 0,
                    "example": 50000.00
                },
                "house_allowance": {
                    "type": "number",
                    "minimum": 0,
                    "example": 20000.00
                },
                "transport_allowance": {
                    "type": "number",
                    "minimum": 0,
                    "example": 10000.00
                },
                "other_allowances": {
                    "type": "number",
                    "minimum": 0,
                    "example": 5000.00
                },
                "bank_name": {
                    "type": "string",
                    "maxLength": 50,
                    "example": "Equity Bank"
                },
                "bank_account": {
                    "type": "string",
                    "maxLength": 30,
                    "example": "0123456789"
                },
                "department": {
                    "type": "string",
                    "maxLength": 50,
                    "example": "Finance"
                },
                "position": {
                    "type": "string",
                    "maxLength": 50,
                    "example": "Accountant"
                },
                "hire_date": {
                    "type": "string",
                    "format": "date",
                    "example": "2024-01-15"
                },
                "is_active": {
                    "type": "boolean",
                    "example": True
                },
                "tax_relief": {
                    "type": "number",
                    "minimum": 0,
                    "example": 2400.00
                }
            }
        }
    
    def _transaction_schema(self) -> Dict[str, Any]:
        """Schema for transaction data."""
        return {
            "type": "object",
            "required": ["date", "amount", "description"],
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "maxLength": 50,
                    "example": "TXN20241201001"
                },
                "date": {
                    "type": "string",
                    "format": "date",
                    "example": "2024-12-01"
                },
                "amount": {
                    "type": "number",
                    "example": 15000.00
                },
                "description": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    "example": "Office supplies purchase"
                },
                "vendor": {
                    "type": "string",
                    "maxLength": 100,
                    "example": "Acme Supplies Ltd"
                },
                "reference": {
                    "type": "string",
                    "maxLength": 50,
                    "example": "INV-2024-001"
                },
                "category": {
                    "type": "string",
                    "maxLength": 50,
                    "example": "Office Expenses"
                },
                "account_code": {
                    "type": "string",
                    "maxLength": 10,
                    "example": "5200"
                },
                "tax_amount": {
                    "type": "number",
                    "minimum": 0,
                    "example": 2400.00
                },
                "net_amount": {
                    "type": "number",
                    "example": 12600.00
                },
                "currency": {
                    "type": "string",
                    "enum": ["KES", "USD", "EUR", "GBP"],
                    "example": "KES"
                },
                "exchange_rate": {
                    "type": "number",
                    "minimum": 0,
                    "example": 1.0
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "approved", "posted", "cancelled"],
                    "example": "pending"
                }
            }
        }
    
    def _payroll_line_schema(self) -> Dict[str, Any]:
        """Schema for payroll line items."""
        return {
            "type": "object",
            "required": ["employee_id", "payroll_period", "gross_salary"],
            "properties": {
                "employee_id": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 20,
                    "example": "EMP001"
                },
                "payroll_period": {
                    "type": "string",
                    "pattern": "^[0-9]{4}-[0-9]{2}$",
                    "example": "2024-12"
                },
                "gross_salary": {
                    "type": "number",
                    "minimum": 0,
                    "example": 80000.00
                },
                "basic_salary": {
                    "type": "number",
                    "minimum": 0,
                    "example": 50000.00
                },
                "house_allowance": {
                    "type": "number",
                    "minimum": 0,
                    "example": 20000.00
                },
                "transport_allowance": {
                    "type": "number",
                    "minimum": 0,
                    "example": 10000.00
                },
                "other_allowances": {
                    "type": "number",
                    "minimum": 0,
                    "example": 0.00
                },
                "overtime_hours": {
                    "type": "number",
                    "minimum": 0,
                    "example": 0.0
                },
                "overtime_rate": {
                    "type": "number",
                    "minimum": 0,
                    "example": 0.0
                },
                "bonus": {
                    "type": "number",
                    "minimum": 0,
                    "example": 0.0
                },
                "days_worked": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 31,
                    "example": 22
                },
                "days_in_month": {
                    "type": "integer",
                    "minimum": 28,
                    "maximum": 31,
                    "example": 30
                }
            }
        }
    
    def _chart_of_accounts_schema(self) -> Dict[str, Any]:
        """Schema for chart of accounts."""
        return {
            "type": "object",
            "required": ["account_code", "account_name", "account_type"],
            "properties": {
                "account_code": {
                    "type": "string",
                    "pattern": "^[0-9]{4,6}$",
                    "example": "1100"
                },
                "account_name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "example": "Cash and Bank"
                },
                "account_type": {
                    "type": "string",
                    "enum": ["asset", "liability", "equity", "revenue", "expense"],
                    "example": "asset"
                },
                "parent_code": {
                    "type": "string",
                    "pattern": "^[0-9]{4,6}$",
                    "example": "1000"
                },
                "is_active": {
                    "type": "boolean",
                    "example": True
                },
                "description": {
                    "type": "string",
                    "maxLength": 200,
                    "example": "All cash and bank accounts"
                }
            }
        }
    
    def _tax_config_schema(self) -> Dict[str, Any]:
        """Schema for tax configuration settings."""
        return {
            "type": "object",
            "required": ["config_key", "config_value", "effective_date"],
            "properties": {
                "config_key": {
                    "type": "string",
                    "enum": ["vat_rate", "paye_relief", "nssf_rate", "nhif_rates", "vendor_tax_status"],
                    "example": "vat_rate"
                },
                "config_value": {
                    "type": "string",
                    "example": "0.16"
                },
                "effective_date": {
                    "type": "string",
                    "format": "date",
                    "example": "2024-01-01"
                },
                "description": {
                    "type": "string",
                    "maxLength": 200,
                    "example": "Standard VAT rate for Kenya"
                },
                "is_active": {
                    "type": "boolean",
                    "example": True
                }
            }
        }
    
    def _approval_schema(self) -> Dict[str, Any]:
        """Schema for approval workflow configuration."""
        return {
            "type": "object",
            "required": ["transaction_type", "amount_threshold", "approver_role"],
            "properties": {
                "transaction_type": {
                    "type": "string",
                    "enum": ["expense", "vendor_payment", "payroll", "journal_entry"],
                    "example": "expense"
                },
                "amount_threshold": {
                    "type": "number",
                    "minimum": 0,
                    "example": 50000.00
                },
                "approver_role": {
                    "type": "string",
                    "enum": ["finance_manager", "ceo", "department_head"],
                    "example": "finance_manager"
                },
                "requires_documents": {
                    "type": "boolean",
                    "example": True
                },
                "auto_approve": {
                    "type": "boolean",
                    "example": False
                }
            }
        }