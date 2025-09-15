# LedgerOne-3
LedgerOne

# 🇰🇪 AI-Powered Ledger System (Kenya-Specific)

An **enterprise-grade financial and accounting system** built in **Streamlit** with **ML-powered automation**.  
Designed for **Kenyan businesses (2025)** — including **Payroll, PAYE, NSSF, NHIF, VAT, Forecasting, Fraud Detection, Integrations (QuickBooks, Excel, API), OCR ingestion, and more**.

---

## ✨ Features

### 🔑 Core
- Multi-tenant support (separate data per company).
- Role-based access control:
  - Superadmin (developer)
  - Tenant Admin
  - Accountant
  - Finance Manager
  - CEO
- Audit logs for all critical actions.
- JSON-based storage (upgradeable to PostgreSQL).

### 💼 Accounting Workflow
1. **Data Ingestion**
   - CSV / Excel / JSON
   - QuickBooks Online (simulated, API-ready)
   - REST API fetch
   - OCR (PDF/Image invoices)
2. **Reconciliation**
   - Matches staging data vs transactions
   - Vendor normalization (ML)
   - Flags unmatched items
3. **Posting**
   - Chart of Accounts (Kenya-specific)
   - Journal entries
   - Balanced books
4. **Financial Reports**
   - Trial Balance
   - Balance Sheet
   - Profit & Loss

### 🇰🇪 Payroll & Tax (2025)
- **PAYE (progressive bands)**
- **NSSF Tier I & II (6% employee + employer, capped)**
- **NHIF (2025 contribution bands)**
- **VAT (16%)**

### 🤖 AI & ML
- Vendor normalization (string similarity + ML).
- Forecasting (Prophet → fallback XGBoost → fallback naive).
- Fraud detection (IsolationForest).
- Workflow/role suggestions.

### 🔌 Integrations
- QuickBooks Online (placeholder for OAuth2 API).
- Excel connector.
- REST API ingestion.
- OCR ingestion (Tesseract / pdf2image).

### 🧪 Testing
- Full pytest suite for every module:
  - Auth, Parser, OCR, Ingestion, Reconciliation, Posting, Reports, Payroll, Forecast, Fraud, Integrations.

---

## 📂 Folder Structure

ledger_streamlit/ ├── streamlit_app.py ├── ledger/ │   ├── auth/roles.py │   ├── ingest/{parser,ocr,engine}.py │   ├── reconcile/engine.py │   ├── ledger/posting.py │   ├── reports/financials.py │   ├── tax/payroll.py │   ├── ml/{vendor_normalizer,forecast,fraud}.py │   └── integrations/connectors.py ├── data/ │   ├── tenants/ │   ├── transactions/ │   ├── staging/ │   ├── reconcile/ │   ├── ledger/ │   ├── fraud/ │   └── logs/ └── tests/ └── test_*.py

---

## 🚀 Usage

### 1. Install dependencies
```bash
pip install -r requirements.txt

2. Run Streamlit app

streamlit run streamlit_app.py

3. Login & Workflow

Superadmin credentials seeded automatically.

Tenant admin creates roles (CEO, Accountant, Finance Manager).

Workflows suggested by AI, editable in UI.

Choose sidebar tabs:

Ingestion

Reconciliation

Posting

Reports

Payroll/Tax

Forecasting

Fraud Detection

Integrations




---

🧪 Testing

Run full test suite:

pytest -q


---

📊 Example Scenarios

1. Waste Management Company (50 trucks, Nairobi)

Upload Excel of fuel invoices.

OCR import PDF invoices from suppliers.

Reconcile against bank transactions.

Post expenses to Fleet Costs (5200).

View Profit & Loss.



2. Retail Chain

QuickBooks API sync for daily sales.

VAT computed automatically.

Forecast next 12 months sales with Prophet.



3. Logistics Firm

Payroll module computes PAYE, NSSF, NHIF for 500+ employees.

Fraud detection flags outlier payments.

Reports accessible to CEO & Finance Manager.





---

⚠️ Notes

OCR requires tesseract-ocr installed locally.

QuickBooks API currently simulated — OAuth2 integration ready.

Default storage = JSON → can be migrated to PostgreSQL in production.



---

🛠 Requirements

See requirements.txt for Python dependencies.


---

👨‍💻 Author

Built with ❤️ for Kenyan businesses.



