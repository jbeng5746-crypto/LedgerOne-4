# LedgerOne-3 - AI-Powered Ledger System

## Project Overview
LedgerOne-3 is an enterprise-grade financial and accounting system built in Streamlit with ML-powered automation, specifically designed for Kenyan businesses. The system includes payroll, PAYE, NSSF, NHIF, VAT calculations, forecasting, fraud detection, and various integrations.

## Recent Changes (2025-09-12)
- Successfully imported GitHub repository and set up in Replit environment
- Extracted complete Streamlit application from Jupyter notebook
- Installed all required Python dependencies
- Configured Streamlit to run on 0.0.0.0:5000 with proper host header configuration
- Set up workflow for automatic application startup
- Configured deployment settings for autoscale deployment
- Application is fully functional and accessible via web interface

## Project Architecture
### Technology Stack
- **Frontend**: Streamlit web application
- **Backend**: Python with SQLAlchemy for data persistence
- **ML/AI**: Prophet, XGBoost, scikit-learn for forecasting and fraud detection
- **Data Storage**: JSON-based (upgradeable to PostgreSQL)
- **OCR**: Tesseract with pdf2image for document processing

### Key Components
- **Authentication & Roles**: Multi-tenant with role-based access control
- **Data Ingestion**: CSV/Excel/JSON/PDF/Image support with OCR
- **Reconciliation Engine**: ML-powered transaction matching
- **Ledger Posting**: Kenya-specific chart of accounts
- **Financial Reports**: Trial Balance, Balance Sheet, P&L
- **Payroll & Tax**: 2025 Kenyan tax calculations (PAYE, NSSF, NHIF, VAT)
- **ML Features**: Vendor normalization, forecasting, fraud detection
- **Integrations**: QuickBooks, Excel, REST API connectors

### Directory Structure
```
ledger_streamlit/
├── streamlit_app.py          # Main application entry point
├── .streamlit/config.toml    # Streamlit configuration
├── ledger/                   # Core application modules
│   ├── auth/                 # Authentication and roles
│   ├── ingest/               # Data ingestion and OCR
│   ├── reconcile/            # Transaction reconciliation
│   ├── ledger/               # Posting and accounting
│   ├── reports/              # Financial reporting
│   ├── tax/                  # Payroll and tax calculations
│   ├── ml/                   # Machine learning features
│   └── integrations/         # External connectors
├── data/                     # Application data storage
├── tests/                    # Test suite
└── migrations/               # Database migrations
```

## Configuration
### Streamlit Configuration
- Server address: 0.0.0.0:5000
- CORS disabled for development
- XSRF protection disabled for development
- Host header verification bypassed for Replit proxy

### Deployment
- Target: Autoscale deployment
- Suitable for stateless web applications
- Automatic scaling based on traffic

## User Preferences
- Production-ready application with real data (no mock/placeholder data)
- Focus on Kenyan business requirements and tax compliance
- Comprehensive test coverage with pytest
- Role-based access control for different user types

## Next Steps for Development
1. **Optional Improvements**:
   - Install python-Levenshtein for faster fuzzy matching
   - Add plotly for interactive charts
   - Consider PostgreSQL migration for production

2. **Testing**:
   - Run pytest suite to verify all modules
   - Test OCR functionality with sample documents
   - Validate tax calculations with current Kenya rates

3. **Production Readiness**:
   - Review and update security settings
   - Configure proper authentication flow
   - Set up backup and recovery procedures