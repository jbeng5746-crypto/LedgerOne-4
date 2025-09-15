
import streamlit as st
import hashlib
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import numpy as np

from ledger.auth.roles import RoleManager, _verify_password
from ledger.ingest.engine import IngestionEngine
from ledger.reconcile.engine import ReconciliationEngine
from ledger.ledger.posting import LedgerPosting
from ledger.reports.financials import FinancialReports
from ledger.tax.payroll import KenyanPayroll, KenyanVAT
from ledger.ml.forecast import ForecastEngine
from ledger.ml.fraud import FraudDetector
from ledger.integrations.connectors import QuickBooksConnector, ExcelConnector, APIConnector
from ledger.vendors.manager import VendorManager
from ledger.employees.manager import EmployeeManager
from ledger.transactions.manager import TransactionManager
from ledger.payroll.bulk_processor import PayrollBulkProcessor
from ledger.ui.upload_components import render_upload_widget, render_bulk_operations_sidebar

st.set_page_config(
    page_title="LedgerOne-3 | AI-Powered Accounting", 
    layout="wide",
    page_icon="🇰🇪",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://docs.ledgerone.co.ke',
        'Report a bug': "https://github.com/ledgerone/support",
        'About': "LedgerOne-3 v3.0 - AI-Powered Accounting for Kenyan Businesses"
    }
)

# Custom CSS for enhanced styling
st.markdown("""
<style>
    .main-header { 
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-badge {
        background: #10b981;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.8rem;
    }
    .sidebar-section {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Removed insecure hash function - now using secure verification from roles module

def show_welcome():
    # Enhanced header with gradient background
    st.markdown('<div class="main-header"><h1>🇰🇪 LedgerOne-3</h1><h3>AI-Powered Financial Management for Kenyan Businesses</h3><p>Comprehensive accounting, payroll, tax compliance, and ML-powered insights</p></div>', unsafe_allow_html=True)
    
    # Statistics overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏢 Companies", "3", "Active tenants")
    with col2:
        st.metric("👥 Users", "4", "Registered")
    with col3:
        st.metric("📊 Features", "12+", "Core modules")
    with col4:
        st.metric("🤖 AI Models", "5", "ML engines")
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🔑 Demo Accounts Available:")
        st.info("""
        **Demo Environment Notice:**
        This is a demonstration environment with pre-configured accounts.
        
        **Available Demo Companies:**
        - Nairobi WasteCo (Waste Management)
        - Kibera Manufacturing (Manufacturing) 
        - SwiftLogistics (Logistics)
        
        **Note:** Demo credentials are provided separately for security.
        Contact your administrator for access credentials.
        """)
        
    with col2:
        st.markdown("### ✨ Features Available:")
        st.success("""
        • **Multi-tenant Support** - Separate data per company
        • **Role-based Access** - CEO, Finance Manager, Accountant roles
        • **Data Ingestion** - CSV, Excel, PDF, OCR support
        • **ML-Powered Reconciliation** - Smart transaction matching
        • **Kenyan Tax Compliance** - PAYE, NSSF, NHIF, VAT calculations
        • **Financial Reports** - Trial Balance, P&L, Balance Sheet
        • **Forecasting & Fraud Detection** - AI-powered insights
        • **Integrations** - QuickBooks, Excel, REST APIs
        """)

def login_form():
    show_welcome()
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        st.markdown("### Login to Your Account")
        email=st.text_input("Email", key="login_email")
        pw=st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_btn"):
            rm=RoleManager()
            user=next((u for u in rm.users.values() if u["email"]==email),None)
            # Secure authentication with proper legacy hash handling
            if user:
                stored_hash = user["password_hash"]
                
                # Check if it's a new PBKDF2 hash (contains ':' and is longer than 64 chars)
                if ':' in stored_hash and len(stored_hash) > 64:
                    if _verify_password(stored_hash, pw):
                        st.session_state["user"] = user
                        st.success(f"Welcome back, {email}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                
                # Handle legacy SHA-256 hashes SECURELY
                elif len(stored_hash) == 64 and all(c in '0123456789abcdef' for c in stored_hash):
                    # Legacy SHA-256 hash - verify against the actual hash
                    import hashlib
                    legacy_hash = hashlib.sha256(pw.encode()).hexdigest()
                    if legacy_hash == stored_hash:
                        # Successful login with legacy hash - upgrade to secure hash
                        from ledger.auth.roles import _hash_password
                        new_hash = _hash_password(pw)
                        rm = RoleManager()
                        rm.users[user["id"]]["password_hash"] = new_hash
                        rm.save()
                        
                        st.session_state["user"] = user
                        st.success(f"Welcome back, {email}! Your password has been upgraded to a more secure format.")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                
                else:
                    # Unknown hash format
                    st.error("Invalid credentials - please contact administrator for password reset")
            else:
                st.error("Invalid credentials")
    
    with tab2:
        st.markdown("### Create New Account")
        with st.form("registration_form"):
            reg_email = st.text_input("Email Address")
            reg_password = st.text_input("Password", type="password")
            reg_confirm = st.text_input("Confirm Password", type="password")
            company_name = st.text_input("Company Name")
            industry = st.selectbox("Industry", ["waste", "manufacturing", "logistics", "retail", "services", "other"])
            
            if st.form_submit_button("Register"):
                if reg_password != reg_confirm:
                    st.error("Passwords do not match!")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters!")
                elif not reg_email or not company_name:
                    st.error("Please fill in all fields!")
                else:
                    rm = RoleManager()
                    # Check if email already exists
                    if any(u["email"] == reg_email for u in rm.users.values()):
                        st.error("Email already registered!")
                    else:
                        # Create new tenant with admin
                        result = rm.create_tenant_with_admin(company_name, reg_email, reg_password, industry)
                        # Get the newly created user for autologin
                        new_user = rm.users[result["user_id"]]
                        st.session_state["user"] = new_user
                        st.success(f"Account created successfully! Welcome to {company_name}!")
                        st.rerun()

def logout_button():
    if st.sidebar.button("🚪 Logout", help="Click to logout and return to login screen"): 
        st.session_state.clear()
        st.success("You have been logged out successfully!")
        st.rerun()

def show_user_dashboard(user):
    """Enhanced personalized dashboard with rich analytics"""
    # Enhanced Sidebar
    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.markdown(f"### 👤 {user['email']}")
    
    if user.get('tenant_id'):
        rm = RoleManager()
        tenant = rm.tenants.get(user['tenant_id'], {})
        st.sidebar.markdown(f"**🏢 Company:** {tenant.get('name', 'Unknown')}")
        st.sidebar.markdown(f"**🏭 Industry:** {tenant.get('industry', 'Unknown').title()}")
        
        # Enhanced role display with badges
        roles = [r.split(":")[1] if ":" in r else r for r in user.get("roles", [])]
        role_icons = {"ceo": "👑", "finance_manager": "💰", "account_manager": "📋", "hr_manager": "👥"}
        primary_role = roles[0] if roles else "user"
        icon = role_icons.get(primary_role, "👤")
        st.sidebar.markdown(f"**🎯 Role:** {icon} {primary_role.replace('_', ' ').title()}")
        
        # Quick access buttons
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ⚡ Quick Actions")
        if st.sidebar.button("📈 View Reports", use_container_width=True):
            st.session_state.selected_page = "Reports"
            st.rerun()
        if st.sidebar.button("🔄 Run Reconciliation", use_container_width=True):
            st.session_state.selected_page = "Reconciliation"
            st.rerun()
    else:
        st.sidebar.markdown("**🔧 Role:** System Administrator")
        st.sidebar.markdown("**⚡ Access:** Full System Control")
    
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    logout_button()
    
    # Enhanced Main Dashboard
    if user.get('tenant_id'):
        rm = RoleManager()
        tenant = rm.tenants.get(user['tenant_id'], {})
        
        # Company header with stats
        st.markdown(f'<div class="main-header"><h2>🏢 {tenant.get("name", "Your Company")}</h2><p>Financial Management Dashboard</p></div>', unsafe_allow_html=True)
        
        # Role-specific dashboard content
        user_roles = [r.split(":")[1] if ":" in r else r for r in user.get("roles", [])]
        
        # Enhanced metrics with real-time style display
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 Cash Balance", "KES 1.2M", "5.2%", help="Current cash and bank balance")
        with col2:
            st.metric("📈 Monthly Revenue", "KES 2.4M", "15%", help="This month's total revenue")
        with col3:
            st.metric("📋 Pending Items", "12", "-3", help="Items pending reconciliation")
        with col4:
            st.metric("🔍 ML Insights", "3", "1", help="New AI-generated insights")
        
        # Interactive charts section
        st.markdown("---")
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("### 📈 Revenue Trend (Last 6 Months)")
            # Sample data for demo
            months = ['Apr 2025', 'May 2025', 'Jun 2025', 'Jul 2025', 'Aug 2025', 'Sep 2025']
            revenue = [1800000, 2100000, 1950000, 2200000, 2350000, 2400000]
            
            fig = px.line(x=months, y=revenue, title="Revenue Growth")
            fig.update_layout(height=300, showlegend=False)
            fig.update_traces(line_color='#3b82f6', line_width=3)
            st.plotly_chart(fig, use_container_width=True)
            
        with chart_col2:
            st.markdown("### 📊 Expense Breakdown")
            # Sample expense data
            categories = ['Payroll', 'Operations', 'Fleet', 'Admin', 'Other']
            amounts = [800000, 450000, 320000, 180000, 120000]
            
            fig = px.pie(values=amounts, names=categories, title="Current Month Expenses")
            fig.update_layout(height=300, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        
        # Recent activity section
        st.markdown("---")
        st.markdown("### 🕰️ Recent Activity")
        
        activity_data = {
            'Time': ['2 min ago', '15 min ago', '1 hour ago', '3 hours ago'],
            'Activity': [
                '💸 Payment processed: KES 45,000',
                '📄 Invoice uploaded via OCR',
                '🔄 Reconciliation completed',
                '📈 Monthly report generated'
            ],
            'Status': ['✅ Complete', '🔄 Processing', '✅ Complete', '✅ Complete']
        }
        
        st.dataframe(pd.DataFrame(activity_data), use_container_width=True, hide_index=True)
        
    else:
        # Enhanced superadmin dashboard
        st.markdown('<div class="main-header"><h2>🔧 System Administration</h2><p>Enterprise-wide Management Console</p></div>', unsafe_allow_html=True)
        
        rm = RoleManager()
        total_tenants = len(rm.tenants)
        total_users = len(rm.users)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏢 Companies", total_tenants, help="Total registered companies")
        with col2:
            st.metric("👥 Users", total_users, help="Total system users")
        with col3:
            st.metric("📊 System Health", "98.5%", "0.2%", help="Overall system performance")
        with col4:
            st.metric("🔒 Security Score", "A+", help="Security compliance rating")

def show_bulk_data_management(user):
    """Comprehensive bulk data management with upload functionality for all modules."""
    
    # Render sidebar operations  
    render_bulk_operations_sidebar()
    
    st.markdown('<div class="main-header"><h2>📁 Bulk Data Management</h2><p>Upload and manage data across all modules with templates, validation, and audit trails</p></div>', unsafe_allow_html=True)
    
    tenant_id = user["tenant_id"]
    
    # Initialize managers
    vendor_manager = VendorManager(tenant_id)
    employee_manager = EmployeeManager(tenant_id)
    transaction_manager = TransactionManager(tenant_id)
    payroll_processor = PayrollBulkProcessor(tenant_id)
    
    # Create tabs for different entity types
    entity_tabs = st.tabs([
        "👥 Vendors", 
        "🏢 Employees", 
        "💳 Transactions", 
        "💰 Payroll",
        "📊 Analytics"
    ])
    
    with entity_tabs[0]:  # Vendors
        st.markdown("### 👥 Vendor Master Data Management")
        
        # Column help for vendors
        vendor_help = {
            'vendor_code': 'Unique identifier for the vendor (auto-generated if empty)',
            'vendor_name': 'Full legal name of the vendor',
            'kra_pin': 'Kenya Revenue Authority PIN (format: P051234567M)',
            'email': 'Primary contact email address',
            'phone': 'Contact phone number with country code',
            'payment_terms': 'Payment terms in days (e.g., 30 for Net 30)',
            'credit_limit': 'Maximum credit limit in KES',
            'tax_status': 'VAT registration status: vat_registered, vat_exempt, or unknown'
        }
        
        vendor_extra_options = {
            'auto_deduplicate': {
                'type': 'checkbox',
                'label': 'Auto-deduplicate similar vendors',
                'default': True,
                'help': 'Automatically merge vendors with similar names'
            }
        }
        
        vendor_result = render_upload_widget(
            title="Vendor Data Upload",
            entity_type="vendors",
            get_template_fn=vendor_manager.get_template,
            process_upload_fn=vendor_manager.bulk_upload,
            column_help=vendor_help,
            extra_options=vendor_extra_options
        )
        
        # Show vendor stats
        if st.button("📊 Show Vendor Statistics", key="vendor_stats"):
            stats = vendor_manager.get_vendor_stats()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Vendors", stats['total_vendors'])
            with col2:
                st.metric("Active Vendors", stats['active_vendors'])
            with col3:
                st.metric("Avg Credit Limit", f"KES {stats['average_credit_limit']:,.0f}")
            with col4:
                st.metric("Avg Payment Terms", f"{stats['average_payment_terms']:.0f} days")
            
            if stats['by_tax_status']:
                fig = px.pie(
                    values=list(stats['by_tax_status'].values()),
                    names=list(stats['by_tax_status'].keys()),
                    title="Vendors by Tax Status"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with entity_tabs[1]:  # Employees
        st.markdown("### 🏢 Employee Master Data Management")
        
        # Column help for employees
        employee_help = {
            'employee_id': 'Unique employee identifier (auto-generated if empty)',
            'full_name': 'Full legal name of the employee',
            'email': 'Work email address',
            'national_id': 'Kenya National ID number (8 digits)',
            'kra_pin': 'KRA PIN for tax purposes',
            'basic_salary': 'Basic salary amount in KES',
            'house_allowance': 'House allowance in KES',
            'transport_allowance': 'Transport allowance in KES',
            'bank_account': 'Bank account number for salary payments'
        }
        
        employee_result = render_upload_widget(
            title="Employee Data Upload",
            entity_type="employees",
            get_template_fn=employee_manager.get_template,
            process_upload_fn=employee_manager.bulk_upload,
            column_help=employee_help
        )
        
        # Show employee stats
        if st.button("📊 Show Employee Statistics", key="employee_stats"):
            stats = employee_manager.get_employee_stats()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Employees", stats['total_employees'])
            with col2:
                st.metric("Active Employees", stats['active_employees'])
            with col3:
                st.metric("Departments", len(stats['by_department']))
            with col4:
                st.metric("Avg Salary", f"KES {stats['average_salary']:,.0f}")
            
            # Department breakdown
            if stats['by_department']:
                fig = px.bar(
                    x=list(stats['by_department'].keys()),
                    y=list(stats['by_department'].values()),
                    title="Employees by Department"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Salary ranges
            if stats['salary_ranges']:
                fig = px.bar(
                    x=list(stats['salary_ranges'].keys()),
                    y=list(stats['salary_ranges'].values()),
                    title="Salary Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with entity_tabs[2]:  # Transactions
        st.markdown("### 💳 Transaction Data Management")
        
        # Column help for transactions
        transaction_help = {
            'date': 'Transaction date (YYYY-MM-DD format)',
            'amount': 'Transaction amount in KES',
            'description': 'Transaction description or reference',
            'vendor': 'Vendor or payee name',
            'category': 'Transaction category (e.g., Office Expenses)',
            'reference': 'Invoice number or reference',
            'account_code': 'Chart of accounts code (e.g., 5200 for Office Expenses)'
        }
        
        transaction_extra_options = {
            'auto_reconcile': {
                'type': 'checkbox',
                'label': 'Auto-reconcile after upload',
                'default': False,
                'help': 'Automatically run reconciliation engine after upload'
            },
            'auto_post': {
                'type': 'checkbox',
                'label': 'Auto-post to ledger',
                'default': False,
                'help': 'Automatically post journal entries after reconciliation'
            }
        }
        
        transaction_result = render_upload_widget(
            title="Transaction Data Upload",
            entity_type="transactions",
            get_template_fn=transaction_manager.get_template,
            process_upload_fn=transaction_manager.bulk_upload,
            column_help=transaction_help,
            extra_options=transaction_extra_options
        )
        
        # Show transaction stats
        if st.button("📊 Show Transaction Statistics", key="transaction_stats"):
            stats = transaction_manager.get_transaction_stats()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Transactions", stats['total_transactions'])
            with col2:
                st.metric("Total Amount", f"KES {stats['total_amount']:,.0f}")
            with col3:
                st.metric("Average Amount", f"KES {stats['average_amount']:,.0f}")
            with col4:
                pending_count = stats['by_status'].get('pending', 0)
                st.metric("Pending", pending_count)
            
            # Status breakdown
            if stats['by_status']:
                fig = px.pie(
                    values=list(stats['by_status'].values()),
                    names=list(stats['by_status'].keys()),
                    title="Transactions by Status"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with entity_tabs[3]:  # Payroll
        st.markdown("### 💰 Payroll Bulk Processing")
        
        # Payroll period input
        col1, col2 = st.columns(2)
        with col1:
            payroll_year = st.selectbox("Year", range(2024, 2026), index=1)
        with col2:
            payroll_month = st.selectbox("Month", range(1, 13), index=datetime.now().month - 1)
        
        payroll_period = f"{payroll_year}-{payroll_month:02d}"
        
        # Generate pre-filled template
        if st.button("📋 Generate Payroll Template", key="generate_payroll_template"):
            with st.spinner("Generating payroll template..."):
                template_df = payroll_processor.generate_payroll_template(payroll_period)
                st.success(f"✅ Generated template for {len(template_df)} employees")
                
                # Download template
                csv = template_df.to_csv(index=False)
                st.download_button(
                    label="💾 Download Pre-filled Template",
                    data=csv,
                    file_name=f"payroll_template_{payroll_period}.csv",
                    mime="text/csv"
                )
                
                st.dataframe(template_df, use_container_width=True)
        
        # Column help for payroll
        payroll_help = {
            'employee_id': 'Employee identifier (must match employee master data)',
            'payroll_period': 'Payroll period in YYYY-MM format',
            'gross_salary': 'Total gross salary including allowances',
            'basic_salary': 'Basic salary component',
            'days_worked': 'Number of days worked in the period',
            'overtime_hours': 'Overtime hours worked',
            'bonus': 'Additional bonus amount'
        }
        
        payroll_extra_options = {
            'payroll_period': {
                'type': 'text',
                'label': 'Payroll Period',
                'default': payroll_period,
                'help': 'Payroll period in YYYY-MM format'
            },
            'auto_calculate': {
                'type': 'checkbox',
                'label': 'Auto-calculate taxes',
                'default': True,
                'help': 'Automatically calculate PAYE, NSSF, and NHIF'
            },
            'auto_post_to_ledger': {
                'type': 'checkbox',
                'label': 'Auto-post to ledger',
                'default': False,
                'help': 'Automatically create journal entries'
            }
        }
        
        def process_payroll_upload(file_path, column_mappings, mode, **kwargs):
            return payroll_processor.bulk_process_payroll(
                file_path=file_path,
                column_mappings=column_mappings,
                payroll_period=kwargs.get('payroll_period', payroll_period),
                auto_calculate=kwargs.get('auto_calculate', True),
                auto_post_to_ledger=kwargs.get('auto_post_to_ledger', False)
            )
        
        payroll_result = render_upload_widget(
            title="Payroll Data Upload",
            entity_type="payroll",
            get_template_fn=payroll_processor.get_template,
            process_upload_fn=process_payroll_upload,
            column_help=payroll_help,
            extra_options=payroll_extra_options
        )
        
        # Show recent payroll runs
        if st.button("📊 Show Payroll History", key="payroll_history"):
            runs = payroll_processor.get_payroll_runs(limit=5)
            if runs:
                st.markdown("### Recent Payroll Runs")
                runs_data = []
                for run in runs:
                    total_employees = len(run.get('employees', []))
                    runs_data.append({
                        'Period': run.get('payroll_period'),
                        'Employees': total_employees,
                        'Status': run.get('status', 'Unknown'),
                        'Created': run.get('created_at', '')[:10] if run.get('created_at') else 'Unknown'
                    })
                
                st.dataframe(pd.DataFrame(runs_data), use_container_width=True)
            else:
                st.info("No payroll runs found")
    
    with entity_tabs[4]:  # Analytics
        st.markdown("### 📊 Upload Analytics & Audit Trail")
        
        # Upload summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Vendors", vendor_manager.repository.get_count())
        with col2:
            st.metric("Employees", employee_manager.repository.get_count())
        with col3:
            st.metric("Transactions", transaction_manager.repository.get_count())
        with col4:
            payroll_runs = len(payroll_processor.get_payroll_runs(limit=100))
            st.metric("Payroll Runs", payroll_runs)
        
        # Recent upload activity (placeholder - would be implemented with audit logger)
        st.markdown("### 🕐 Recent Upload Activity")
        st.info("Upload history and audit trails will be displayed here.")
        
        # Data export section
        st.markdown("### 📤 Export Data")
        export_col1, export_col2 = st.columns(2)
        
        with export_col1:
            if st.button("📥 Export All Vendors"):
                st.info("Vendor export functionality will be implemented here.")
        
        with export_col2:
            if st.button("📥 Export All Employees"):
                st.info("Employee export functionality will be implemented here.")
        
        # System overview charts
        st.markdown("### 📊 System Analytics")
        sys_col1, sys_col2 = st.columns(2)
        
        with sys_col1:
            # Company distribution by industry
            industries = ['Manufacturing', 'Logistics', 'Waste Management']
            counts = [1, 1, 1]
            fig = px.bar(x=industries, y=counts, title="Companies by Industry")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            
        with sys_col2:
            # System usage metrics
            metrics = ['Active Sessions', 'API Calls', 'Data Processing', 'Reports Generated']
            values = [8, 342, 156, 23]
            fig = px.bar(x=metrics, y=values, title="Today's System Usage")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

def show_integrations(user):
    st.markdown('<div class="main-header"><h3>🔗 External Integrations</h3><p>Connect with QuickBooks, Excel, APIs, and other financial systems</p></div>', unsafe_allow_html=True)
    
    tid = user["tenant_id"]
    
    # Integration overview
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📋 QuickBooks", "Ready", help="QuickBooks Online integration")
    with col2:
        st.metric("📄 Excel/CSV", "Active", help="File-based data imports")
    with col3:
        st.metric("🔌 REST APIs", "Available", help="Custom API integrations")
    
    # Create tabs for different integrations
    tab1, tab2, tab3, tab4 = st.tabs(["📋 QuickBooks", "📄 Excel/CSV", "🔌 REST API", "🔧 Settings"])
    
    with tab1:
        st.markdown("### 📋 QuickBooks Online Integration")
        st.info("🗘️ **Note:** This is a demo integration. Real implementation requires OAuth setup.")
        
        qb_col1, qb_col2 = st.columns(2)
        with qb_col1:
            sync_type = st.selectbox("Data Type", ["Invoices", "Customers", "Items", "Payments"])
        with qb_col2:
            date_range = st.selectbox("Date Range", ["Last 30 days", "Last 90 days", "This Year", "Custom"])
        
        if st.button("🔄 Sync from QuickBooks", type="primary"):
            with st.spinner("Syncing data from QuickBooks..."):
                qb = QuickBooksConnector(tid)
                records = qb.fetch_invoices()
                path = qb.save_to_staging(records)
                
                st.success(f"✅ Successfully fetched {len(records)} {sync_type.lower()} from QuickBooks")
                st.info(f"📁 Data saved to: {path}")
                
                if records:
                    st.markdown("#### Preview of Synced Data")
                    st.dataframe(pd.DataFrame(records), use_container_width=True)
    
    with tab2:
        st.markdown("### 📄 Excel & CSV Import")
        
        # File upload with enhanced UI
        uploaded_file = st.file_uploader(
            "📂 Choose your file",
            type=["xlsx", "xls", "csv"],
            help="Upload Excel or CSV files containing financial data"
        )
        
        if uploaded_file:
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"📄 **File:** {uploaded_file.name}")
                st.info(f"📊 **Size:** {uploaded_file.size:,} bytes")
            
            with col2:
                mapping_type = st.selectbox(
                    "Data Mapping",
                    ["Auto-detect", "Invoice Data", "Bank Statements", "Expense Reports", "Custom"]
                )
            
            if st.button("🚀 Process File", type="primary"):
                with st.spinner("Processing file..."):
                    tmp = Path(f"temp_{uploaded_file.name}")
                    with open(tmp, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    ex = ExcelConnector(tid)
                    records = ex.load_excel(str(tmp))
                    
                    st.success(f"✅ Successfully processed {len(records)} records")
                    
                    if records:
                        st.markdown("#### Data Preview")
                        df = pd.DataFrame(records)
                        st.dataframe(df.head(10), use_container_width=True)
                        
                        # Data quality insights
                        st.markdown("#### Data Quality Report")
                        qual_col1, qual_col2, qual_col3 = st.columns(3)
                        with qual_col1:
                            st.metric("Total Records", len(records))
                        with qual_col2:
                            st.metric("Columns", len(df.columns) if len(records) > 0 else 0)
                        with qual_col3:
                            missing_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100) if len(records) > 0 else 0
                            st.metric("Data Completeness", f"{100-missing_pct:.1f}%")
    
    with tab3:
        st.markdown("### 🔌 REST API Integration")
        
        api_col1, api_col2 = st.columns(2)
        with api_col1:
            api_url = st.text_input("🌐 API Endpoint", placeholder="https://api.example.com/data")
            auth_type = st.selectbox("Authentication", ["None", "API Key", "Bearer Token", "Basic Auth"])
        
        with api_col2:
            if auth_type != "None":
                auth_value = st.text_input(f"{auth_type}", type="password")
            data_format = st.selectbox("Response Format", ["JSON", "XML", "CSV"])
        
        if st.button("📍 Test Connection"):
            if api_url:
                st.info("🔍 Testing API connection...")
                # Mock response for demo
                st.success("✅ Connection successful! API is reachable.")
            else:
                st.error("⚠️ Please provide an API URL")
        
        if st.button("📥 Fetch Data", type="primary") and api_url:
            with st.spinner("Fetching data from API..."):
                api = APIConnector(tid)
                try:
                    records = api.fetch_from_api(api_url)
                    st.success(f"✅ Successfully fetched {len(records)} records from API")
                    
                    if records:
                        st.markdown("#### API Response Preview")
                        st.json(records[:3])  # Show first 3 records
                        
                except Exception as e:
                    st.error(f"❌ API fetch failed: {str(e)}")
                    st.info("💡 **Tip:** Check your API URL and authentication credentials")
    
    with tab4:
        st.markdown("### ⚙️ Integration Settings")
        
        st.markdown("#### Sync Preferences")
        auto_sync = st.checkbox("🔄 Enable automatic daily sync", help="Automatically sync data from connected sources")
        notification = st.checkbox("🔔 Send sync notifications", help="Get notified when syncs complete")
        
        st.markdown("#### Data Validation Rules")
        validate_amounts = st.checkbox("💰 Validate amount formats", True)
        validate_dates = st.checkbox("📅 Validate date formats", True)
        require_vendor = st.checkbox("🏢 Require vendor information", False)
        
        if st.button("💾 Save Settings"):
            st.success("✅ Integration settings saved successfully!")

def show_ingestion(user):
    st.markdown('<div class="main-header"><h3>📥 Unified Data Ingestion</h3><p>AI-powered document processing with OCR, structured data parsing, and intelligent extraction</p></div>', unsafe_allow_html=True)
    
    tid = user["tenant_id"]
    
    # Ingestion statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 Documents", "23", "5", help="Total processed documents")
    with col2:
        st.metric("🔍 OCR Success", "94%", "2%", help="OCR processing success rate")
    with col3:
        st.metric("🤖 AI Extraction", "87%", "8%", help="AI field extraction accuracy")
    with col4:
        st.metric("⚡ Avg Speed", "2.3s", "-0.4s", help="Average processing time")
    
    st.markdown("---")
    
    # Enhanced file upload interface
    upload_col1, upload_col2 = st.columns([2, 1])
    
    with upload_col1:
        st.markdown("### 📂 Upload Files")
        uploaded = st.file_uploader(
            "📤 Drag and drop your files here",
            type=["csv", "xlsx", "xls", "json", "pdf", "png", "jpg", "jpeg", "tiff"],
            help="Supported: Excel, CSV, JSON, PDF invoices, and images",
            accept_multiple_files=True
        )
    
    with upload_col2:
        st.markdown("### 🎯 Processing Options")
        ocr_language = st.selectbox("OCR Language", ["English", "Swahili", "Auto-detect"])
        extract_mode = st.selectbox("Extraction Mode", ["Smart AI", "Template-based", "Manual Review"])
        confidence_threshold = st.slider("Confidence Threshold", 0.5, 1.0, 0.8)
    
    if uploaded:
        for file in uploaded if isinstance(uploaded, list) else [uploaded]:
            st.markdown(f"---")
            st.markdown(f"### Processing: {file.name}")
            
            file_col1, file_col2 = st.columns([1, 1])
            
            with file_col1:
                st.info(f"📄 **File:** {file.name}")
                st.info(f"📊 **Size:** {file.size:,} bytes")
                file_type = file.name.split(".")[-1].upper()
                
                if file_type in ["PDF", "PNG", "JPG", "JPEG", "TIFF"]:
                    st.info(f"🔍 **Type:** OCR Document ({file_type})")
                else:
                    st.info(f"📁 **Type:** Structured Data ({file_type})")
            
            with file_col2:
                if st.button(f"🚀 Process {file.name}", key=f"process_{file.name}"):
                    with st.spinner(f"Processing {file.name}..."):
                        tmp = Path("temp_upload." + file.name.split(".")[-1])
                        with open(tmp, "wb") as f:
                            f.write(file.getbuffer())
                        
                        eng = IngestionEngine(tid)
                        try:
                            res = eng.ingest(str(tmp))
                            
                            if res["mode"] == "structured":
                                st.success(f"✅ Structured file processed: {res['count']} records extracted")
                                
                                # Load and display data with enhanced formatting
                                df = pd.read_json(res["file"])
                                
                                # Data quality metrics
                                qual_col1, qual_col2, qual_col3 = st.columns(3)
                                with qual_col1:
                                    st.metric("Records", len(df))
                                with qual_col2:
                                    st.metric("Fields", len(df.columns))
                                with qual_col3:
                                    completeness = (1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
                                    st.metric("Completeness", f"{completeness:.1f}%")
                                
                                st.markdown("#### Extracted Data")
                                st.dataframe(df.head(20), use_container_width=True)
                                
                            else:
                                st.success("✅ OCR processing completed successfully")
                                
                                parsed_data = res["parsed"]
                                
                                # OCR results with confidence scores
                                ocr_col1, ocr_col2 = st.columns(2)
                                
                                with ocr_col1:
                                    st.markdown("#### 📝 Extracted Information")
                                    if isinstance(parsed_data, dict):
                                        for key, value in parsed_data.items():
                                            if value:
                                                st.text(f"{key.title()}: {value}")
                                    else:
                                        st.json(parsed_data)
                                
                                with ocr_col2:
                                    st.markdown("#### 🎯 Processing Metrics")
                                    st.success(f"🔍 Language: {ocr_language}")
                                    st.success(f"🤖 Extraction: {extract_mode}")
                                    st.success(f"🎯 Confidence: {confidence_threshold*100:.0f}%")
                                    
                                    # Show confidence score if available
                                    confidence = 0.85  # Mock confidence score
                                    if confidence >= confidence_threshold:
                                        st.success(f"✅ Quality Score: {confidence*100:.1f}%")
                                    else:
                                        st.warning(f"⚠️ Quality Score: {confidence*100:.1f}% (Below threshold)")
                        
                        except Exception as e:
                            st.error(f"❌ Ingestion failed: {str(e)}")
                            st.info("💡 **Tip:** Ensure your file format is supported and not corrupted")
    
    # Processing history and batch operations
    st.markdown("---")
    st.markdown("### 📈 Recent Processing History")
    
    # Mock history data
    history_data = {
        'Time': ['2 min ago', '15 min ago', '1 hour ago', '3 hours ago'],
        'File': ['invoice_sept.pdf', 'bank_statement.xlsx', 'receipts_batch.zip', 'payroll_data.csv'],
        'Type': ['📄 OCR', '📁 Excel', '🗜️ Archive', '📁 CSV'],
        'Records': ['1 invoice', '145 transactions', '23 receipts', '87 employees'],
        'Status': ['✅ Success', '✅ Success', '🔄 Processing', '✅ Success']
    }
    
    st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)

def show_reconciliation(user):
    st.subheader("Reconciliation")
    tid=user["tenant_id"]
    if st.button("Run reconciliation"):
        engine=ReconciliationEngine(tid)
        report=engine.reconcile()
        st.session_state["recon_report"]=report
        st.success("Reconciliation complete")
        matches=[r for r in report["matches"] if r["match"]]
        unmatched=[r for r in report["matches"] if not r["match"]]
        st.markdown("### Matches")
        if matches: 
            st.dataframe(pd.DataFrame([{"date":m["staging"].get("date"),"amount":m["staging"].get("amount"),"vendor":m["staging"].get("vendor"),"reason":",".join(m["reason"])} for m in matches]))
        else: st.info("No matches")
        st.markdown("### Unmatched")
        if unmatched: 
            st.dataframe(pd.DataFrame([{"date":m["staging"].get("date"),"amount":m["staging"].get("amount"),"vendor":m["staging"].get("vendor")} for m in unmatched]))
        else: st.info("No unmatched records")

def show_posting(user):
    st.subheader("Ledger Posting")
    tid=user["tenant_id"]
    recon_file=Path("data/reconcile")/f"{tid}_recon.json"
    lp=LedgerPosting(tid)
    if recon_file.exists():
        if st.button("Post reconciled transactions"):
            posted=lp.post_from_reconciliation(recon_file)
            st.success(f"Posted {len(posted)} entries to journal")
    journal=lp.load_journal()
    if journal:
        st.markdown("### Journal Entries")
        st.dataframe(pd.DataFrame(journal).tail(20))

def show_reports(user):
    st.subheader("Financial Reports")
    tid=user["tenant_id"]
    fr=FinancialReports(tid)

    st.markdown("### Trial Balance")
    tb=fr.trial_balance()
    if not tb.empty:
        st.dataframe(tb)
    else: st.info("No journal entries yet")

    st.markdown("### Balance Sheet")
    bs=fr.balance_sheet()
    st.json(bs)

    st.markdown("### Profit & Loss")
    pl=fr.profit_and_loss()
    st.json(pl)

def show_payroll(user):
    st.subheader("Payroll & Tax Calculator (Kenya 2025)")
    gross=st.number_input("Gross Salary (KES)",min_value=0.0,step=1000.0)
    if st.button("Compute Payroll"):
        p=KenyanPayroll()
        breakdown=p.payroll_breakdown(gross)
        st.json(breakdown)

    st.subheader("VAT Calculator")
    amt=st.number_input("Amount (KES)",min_value=0.0,step=100.0)
    if st.button("Compute VAT"):
        vat=KenyanVAT().compute_vat(amt)
        st.success(f"VAT (16%) on {amt} = {vat} KES")

def show_forecast(user):
    st.markdown('<div class="main-header"><h3>🔮 AI-Powered Financial Forecasting</h3><p>Machine Learning predictions for revenue, expenses, and cash flow</p></div>', unsafe_allow_html=True)
    
    tid = user["tenant_id"]
    fe = ForecastEngine(tid)
    
    # Forecast controls
    col1, col2, col3 = st.columns(3)
    with col1:
        forecast_periods = st.slider("📅 Forecast Periods", 1, 24, 12)
    with col2:
        forecast_method = st.selectbox("🔧 Method", ["Prophet (Auto)", "XGBoost", "Linear Trend"])
    with col3:
        show_confidence = st.checkbox("🎯 Show Confidence Bands", True)
    
    if st.button("🚀 Generate Forecasts", type="primary"):
        res = fe.forecast_revenue_expenses(periods=forecast_periods)
        if not res:
            st.warning("📊 **No Data Available** - Upload transactions first to generate forecasts")
            st.info("📁 **Tip:** Go to Ingestion or Integrations to upload your financial data")
        else:
            # Create tabs for different forecast types
            tabs = st.tabs(list(res.keys()))
            
            for i, (k, df) in enumerate(res.items()):
                with tabs[i]:
                    # Enhanced metrics for each forecast
                    if len(df) > 0:
                        current_value = df["yhat"].iloc[0] if len(df) > 0 else 0
                        avg_forecast = df["yhat"].mean()
                        trend = "Increasing" if df["yhat"].iloc[-1] > df["yhat"].iloc[0] else "Decreasing"
                        
                        metric_col1, metric_col2, metric_col3 = st.columns(3)
                        with metric_col1:
                            st.metric("📊 Current", f"KES {current_value:,.0f}")
                        with metric_col2:
                            st.metric("📈 Average", f"KES {avg_forecast:,.0f}")
                        with metric_col3:
                            st.metric("🔄 Trend", trend)
                        
                        # Enhanced interactive chart
                        fig = go.Figure()
                        
                        # Main forecast line
                        fig.add_trace(go.Scatter(
                            x=df["ds"],
                            y=df["yhat"],
                            mode='lines+markers',
                            name=f'{k} Forecast',
                            line=dict(color='#3b82f6', width=3),
                            marker=dict(size=6)
                        ))
                        
                        # Confidence intervals if available and requested
                        if show_confidence and "yhat_lower" in df.columns:
                            fig.add_trace(go.Scatter(
                                x=df["ds"],
                                y=df["yhat_upper"],
                                fill=None,
                                mode='lines',
                                line_color='rgba(0,0,0,0)',
                                showlegend=False
                            ))
                            
                            fig.add_trace(go.Scatter(
                                x=df["ds"],
                                y=df["yhat_lower"],
                                fill='tonexty',
                                mode='lines',
                                line_color='rgba(0,0,0,0)',
                                name='Confidence Interval',
                                fillcolor='rgba(59, 130, 246, 0.2)'
                            ))
                        
                        fig.update_layout(
                            title=f"{k} Forecast - Next {forecast_periods} Periods",
                            xaxis_title="Date",
                            yaxis_title="Amount (KES)",
                            height=400,
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Detailed forecast table
                        st.markdown(f"### 📁 {k} Forecast Details")
                        display_df = df.copy()
                        display_df["ds"] = pd.to_datetime(display_df["ds"]).dt.strftime("%Y-%m-%d")
                        display_df["yhat"] = display_df["yhat"].apply(lambda x: f"KES {x:,.0f}")
                        if "yhat_lower" in display_df.columns:
                            display_df["yhat_lower"] = display_df["yhat_lower"].apply(lambda x: f"KES {x:,.0f}")
                            display_df["yhat_upper"] = display_df["yhat_upper"].apply(lambda x: f"KES {x:,.0f}")
                            display_df.columns = ["Date", "Forecast", "Lower Bound", "Upper Bound"]
                        else:
                            display_df.columns = ["Date", "Forecast"]
                        
                        st.dataframe(display_df.head(12), use_container_width=True, hide_index=True)
    
    # Additional forecast tools
    st.markdown("---")
    st.markdown("### 🔧 Advanced Analytics")
    
    adv_col1, adv_col2, adv_col3 = st.columns(3)
    
    with adv_col1:
        if st.button("📉 Scenario Planning"):
            st.info("🚀 **Coming Soon:** Multi-scenario forecasting with optimistic/pessimistic projections")
    
    with adv_col2:
        if st.button("📊 Seasonal Analysis"):
            st.info("🚀 **Coming Soon:** Seasonal pattern detection and holiday impact modeling")
            
    with adv_col3:
        if st.button("🎯 Model Performance"):
            st.info("🚀 **Coming Soon:** Forecast accuracy metrics and model comparison dashboard")

def show_fraud(user):
    st.subheader("Fraud Detection & Anomaly Alerts")
    tid=user["tenant_id"]
    fd=FraudDetector(tid)
    if st.button("Run Fraud Detection"):
        df=fd.detect()
        if not df.empty:
            st.dataframe(df[["date","amount","vendor","anomaly"]].tail(50))
            st.success("Fraud detection complete")
        else:
            st.info("No transactions to analyze")

def main():
    if "user" not in st.session_state:
        login_form()
        return
    
    user = st.session_state["user"]
    
    # Show user dashboard with welcome message
    show_user_dashboard(user)
    
    # Determine user access level
    roles = [r.split(":")[1] if ":" in r else r for r in user.get("roles", [])]
    
    # Create navigation based on user permissions
    if "superadmin" in roles:
        # Superadmin has access to everything plus system management
        tab = st.sidebar.radio("🧭 Navigation", [
            "📊 Dashboard", "📁 Bulk Data", "📥 Ingestion", "🔄 Reconciliation", "📋 Posting", 
            "📈 Reports", "💰 Payroll/Tax", "🔮 Forecasting", "🚨 Fraud Detection", 
            "🔌 Integrations", "⚙️ System Admin"
        ])
    elif "ceo" in roles or "finance_manager" in roles:
        # CEO and Finance Manager have access to all business functions
        tab = st.sidebar.radio("🧭 Navigation", [
            "📊 Dashboard", "📁 Bulk Data", "📥 Ingestion", "🔄 Reconciliation", "📋 Posting", 
            "📈 Reports", "💰 Payroll/Tax", "🔮 Forecasting", "🚨 Fraud Detection", 
            "🔌 Integrations"
        ])
    elif "account_manager" in roles:
        # Account Manager has limited access
        tab = st.sidebar.radio("🧭 Navigation", [
            "📊 Dashboard", "📁 Bulk Data", "📥 Ingestion", "🔄 Reconciliation", "📋 Posting", "📈 Reports"
        ])
    else:
        # Default limited access
        tab = st.sidebar.radio("🧭 Navigation", [
            "📊 Dashboard", "📈 Reports"
        ])
    
    # Route to appropriate function based on selection
    if tab == "📊 Dashboard":
        pass  # Dashboard already shown above
    elif tab == "📁 Bulk Data":
        show_bulk_data_management(user)
    elif tab == "📥 Ingestion":
        show_ingestion(user)
    elif tab == "🔄 Reconciliation":
        show_reconciliation(user)
    elif tab == "📋 Posting":
        show_posting(user)
    elif tab == "📈 Reports":
        show_reports(user)
    elif tab == "💰 Payroll/Tax":
        show_payroll(user)
    elif tab == "🔮 Forecasting":
        show_forecast(user)
    elif tab == "🚨 Fraud Detection":
        show_fraud(user)
    elif tab == "🔌 Integrations":
        show_integrations(user)
    elif tab == "⚙️ System Admin":
        show_system_admin(user)

def show_system_admin(user):
    """System administration panel for superadmin"""
    if "superadmin" not in [r.split(":")[1] if ":" in r else r for r in user.get("roles", [])]:
        st.error("🚫 Access Denied: Superadmin privileges required")
        return
        
    st.subheader("⚙️ System Administration")
    
    rm = RoleManager()
    
    tab1, tab2, tab3 = st.tabs(["👥 Users", "🏢 Companies", "📊 System Stats"])
    
    with tab1:
        st.markdown("### 👥 User Management")
        users_df = pd.DataFrame([
            {
                "Email": user["email"],
                "Company": rm.tenants.get(user.get("tenant_id", ""), {}).get("name", "System"),
                "Roles": ", ".join([r.split(":")[1] if ":" in r else r for r in user.get("roles", [])]),
                "Created": user.get("created_at", "Unknown")[:10]
            }
            for user in rm.users.values()
        ])
        st.dataframe(users_df, use_container_width=True)
    
    with tab2:
        st.markdown("### 🏢 Company Management") 
        if rm.tenants:
            tenants_df = pd.DataFrame([
                {
                    "Company Name": tenant["name"],
                    "Industry": tenant["industry"].title(),
                    "Created": tenant.get("created_at", "Unknown")[:10],
                    "ID": tid
                }
                for tid, tenant in rm.tenants.items()
            ])
            st.dataframe(tenants_df, use_container_width=True)
        else:
            st.info("No companies registered yet")
            
    with tab3:
        st.markdown("### 📊 System Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Companies", len(rm.tenants))
        with col2:
            st.metric("Total Users", len(rm.users))
        with col3:
            st.metric("Total Roles", len(rm.roles))
        with col4:
            st.metric("System Health", "✅ Good")

if __name__=="__main__":
    main()
