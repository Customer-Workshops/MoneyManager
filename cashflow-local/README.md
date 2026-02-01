# CashFlow-Local: Local-First Money Manager

**Production-grade financial management application built with Docker, Streamlit, and DuckDB.**

🏦 Manage your finances locally with automatic transaction deduplication, smart categorization, and visual analytics—all without sending data to the cloud.

---

## 🆕 What's New (February 2026)

### Tax Category Tagging & ITR Filing Support 🆕
- 📋 **Indian Tax Categories:** Tag transactions with 80C, 80D, 80E, 80G, 80TTA, HRA, Section 24, and Business Expenses
- 🏷️ **Multi-tag Support:** Single transaction can have multiple tax categories
- 💰 **Tax Savings Dashboard:** Track YTD deductions and estimated tax savings
- 📊 **Utilization Tracking:** Monitor progress against annual limits (₹1.5L for 80C, ₹25K for 80D, etc.)
- 📥 **Excel Export:** Generate ITR-ready reports for your CA or self-filing
- 🎯 **Smart Alerts:** Color-coded indicators for limit utilization (🟢🟡🔴)
- 📈 **Financial Year Support:** Automatic FY detection (April-March cycle)
### 👥 Multi-User & Family Support (NEW!)
- 🔐 **User Authentication:** Secure email/password login system
- 👨‍👩‍👧‍👦 **Family Workspaces:** Create shared workspaces for families or couples
- 🔑 **Role-Based Access:** Admin, Editor, and Viewer roles with granular permissions
- 💼 **Shared & Personal Accounts:** Mark accounts as shared or private
- 💰 **Shared Budgets:** Set family-wide budget limits
- 🎯 **Shared Goals:** Track savings goals together (vacation, home down payment, etc.)
- 📋 **Activity Log:** See who added, edited, or deleted what
- 👥 **Member Management:** Invite family members, manage roles, and control access

### Enhanced Visual Experience
- ✨ **Category Icons:** Transaction types now display with intuitive emoji icons (💸 Expense, 💰 Income, 🔄 Transfer)
- 📊 **Interactive Charts:** Enhanced tooltips and hover information on all visualizations
- 📈 **Trend Analysis:** Income vs. Expenses chart now includes Net Savings overlay
- 🏪 **Merchant Analysis:** New chart showing top 10 merchants/payees by transaction volume
- 💵 **Smart Budget Tracking:** Color-coded progress bars with visual alerts (🟢🟡🔴)

---

## 🚀 Quick Start

**Prerequisites:**
- Docker & Docker Compose installed ([Get Docker](https://docs.docker.com/get-docker/))

**Launch the application:**

```bash
cd cashflow-local
docker-compose up
```

Open your browser to **http://localhost:8501**

That's it! 🎉

---

## ✨ Features

### 👥 **Multi-User & Family Support**
- **User Accounts:** Secure registration and login system
- **Family Workspaces:** Create shared spaces for managing finances together
- **Role-Based Permissions:**
  - **Admin:** Full access, can add/remove members, manage all settings
  - **Editor:** Add transactions, create budgets and goals
  - **Viewer:** Read-only access to view financial data
- **Shared & Personal Resources:**
  - Mark accounts as shared (joint checking) or personal (my wallet)
  - Create shared budgets accessible to all family members
  - Set shared savings goals (family vacation, emergency fund)
- **Activity Tracking:** Audit log shows who made what changes
- **Member Invitations:** Easily invite family members via email

### 📤 **Universal Statement Ingestion**
- Drag-and-drop upload for **CSV** and **PDF** bank statements
- **Automatic column detection** (works with most bank formats)
- **Enhanced format support:**
  - 7+ date formats (DD/MM/YYYY, DD-MMM-YYYY, YYYY-MM-DD, etc.)
  - Various amount formats (₹1,234.56, (500), 1234.56 Dr, etc.)
  - Smart handling of currency symbols and separators
- **Clear error messages** with actionable troubleshooting tips
- Real-time processing with progress indicators

### 🔄 **Intelligent Deduplication**
- Upload the same statement multiple times—no duplicate transactions
- MD5 hash-based detection: `hash(date + description + amount)`
- Instant feedback on inserted vs. duplicate counts

### 🤖 **Smart Auto-Categorization**
- Keyword-based rule engine (e.g., "Starbucks" → "Coffee")
- Bulk edit categories with "save-as-rule" functionality
- Polars-powered vectorization (5x faster than Pandas)

### 📊 **Visual Analytics Dashboard**
- **KPIs:** Total Balance, Monthly Spend, Income, Savings Rate with icon indicators
- **Line Chart:** Income vs. Expenses trend analysis with Net Savings overlay
- **Donut Chart:** Interactive spending breakdown by category with hover tooltips
- **Bar Chart:** Top Merchants/Payees analysis (last 3 months)
- **Budget Progress Bars:** Color-coded alerts (🟢 < 70%, 🟡 70-90%, 🔴 > 90%)

### 🎨 **Category Icons**
- **Visual Transaction Types:** Icons for easy identification
  - 💸 Expense (Debit) - Outgoing transactions
  - 💰 Income (Credit) - Incoming transactions
  - 🔄 Transfer - Internal transfers
- Displayed consistently across:
  - Dashboard KPI cards
  - Transaction list view
  - Upload confirmation page
  - Category breakdown charts

### 💰 **Budget Management**
- Set monthly spending limits per category
- Visual alerts when you exceed budgets
- Easy-to-use budget configuration interface

### 🏦 **Account Management & Reconciliation**
- Create multiple bank accounts (Checking, Savings, Credit Card, etc.)
- Set opening balances and track current balance
- Multi-currency support (INR, USD, EUR, GBP, JPY)
- Monthly balance reconciliation against bank statements
- Variance detection and analysis
- Duplicate transaction detection
- Balance history timeline visualization
- Comprehensive reconciliation reports

📘 **[Full Reconciliation Guide](docs/RECONCILIATION.md)**

---

## 📁 Project Structure

```
cashflow-local/
├── app.py                 # Main Streamlit application
├── Dockerfile             # Multi-stage Docker build
├── docker-compose.yml     # One-command orchestration
├── requirements.txt       # Python dependencies (pinned versions)
├── category_rules.json    # Categorization rules (editable)
├── .env.example           # Configuration template
├── data/                  # DuckDB database (auto-created)
│   └── cashflow.duckdb
├── src/
│   ├── database.py        # DuckDB connection manager
│   ├── auth.py            # Authentication service
│   ├── workspace.py       # Workspace management
│   ├── parsers.py         # CSV/PDF statement parsers
│   ├── deduplication.py   # Hash-based duplicate detection
│   ├── categorization.py  # Rule-based categorization engine
│   ├── reconciliation.py  # Balance reconciliation & variance detection
│   └── ui/
│       ├── upload_page.py         # File upload interface
│       ├── dashboard_page.py      # KPIs and charts
│       ├── transactions_page.py   # Transaction table with editing
│       ├── budgets_page.py        # Budget configuration
│       ├── accounts_page.py       # Account management
│       └── reconciliation_page.py # Reconciliation workflow
└── tests/
    ├── test_auth.py            # Authentication tests
    ├── test_workspace.py       # Workspace management tests
    ├── test_deduplication.py
    ├── test_parsers.py
    ├── test_reconciliation.py
    └── fixtures/
        └── sample_statement.csv
```

---

## 🔧 Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

**Available Settings:**
```env
APP_NAME=CashFlow-Local
DB_PATH=/app/data/cashflow.duckdb
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

---

## 📋 Supported File Formats

### CSV Files
- **Required Columns:** Date, Description, Amount (or Debit/Credit)
- **Supported Date Formats:** DD/MM/YYYY, DD-MM-YYYY, DD-MMM-YYYY, YYYY-MM-DD, and more
- **Column Name Variations:** Automatically detects common headers like "Trans Date", "Posting Date", "Memo", etc.
- **Amount Formats:** Handles comma-separated amounts, currency symbols (₹, $), accounting format, etc.

**Example CSV:**
```csv
Date,Description,Debit,Credit,Balance
01/09/2025,STARBUCKS #1234,5.50,,1245.50
02/09/2025,Salary Deposit,,3000.00,4245.50
03/09/2025,AMAZON PURCHASE,125.99,,4119.51
```

### PDF Files
- Bank statements with **tabular transaction data**
- Works best with machine-generated PDFs (not scanned images)
- **Currently Tested:** Federal Bank
- **Expected to Work:** Most Indian banks with standard tabular formats
- **Supported Formats:** Multiple date formats, various amount representations

**For detailed format support and troubleshooting, see:**
- 📘 [Parser Documentation](docs/PARSER.md)
- 🔧 [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

---

## 🛠️ Development

### Run Locally (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DB_PATH=./data/cashflow.duckdb
export LOG_LEVEL=DEBUG

# Run Streamlit
streamlit run app.py
```

### Run Tests

```bash
# Inside Docker container
docker exec cashflow-local python -m pytest tests/ -v

# Or locally
pytest tests/ -v
```

---

## 🏗️ Architecture

**Tech Stack:**
- **Frontend:** Streamlit (rapid data visualization)
- **Database:** DuckDB (local OLAP, columnar storage)
- **Data Processing:** Pandas + Polars
- **PDF Parsing:** pdfplumber
- **Containerization:** Docker (multi-stage build, non-root user)

**Performance Highlights:**
- **Deduplication:** O(1) lookups via DuckDB hash index
- **Categorization:** Polars vectorization (5x faster than Pandas)
- **Dashboard Queries:** DuckDB handles 100k+ transactions in <100ms
- **Docker Image:** 450MB (multi-stage build optimization)

---

## 📊 Usage Guide

### 1. First Time Setup
1. Open **http://localhost:8501** in your browser
2. Create an account on the **Register** tab
3. Enter your name, email, and password
4. Optionally set a workspace/family name (defaults to "{Your Name}'s Family")
5. You're automatically logged in as Admin

### 2. Invite Family Members (Optional)
1. Navigate to **👥 Family** page
2. Go to the **Members** tab
3. Enter family member's email and select their role
4. They can register with that email to join your workspace

### 3. Set Up Accounts
1. Go to **👥 Family** → **Accounts** tab
2. Create shared accounts (e.g., "Joint Checking")
3. Create personal accounts (e.g., "My Wallet") - only visible to you

### 4. Upload Bank Statements
1. Navigate to **📤 Upload** page
2. Select which account the transactions belong to
3. Drag-and-drop CSV/PDF files
4. View processing status and duplicate statistics

### 5. Review Dashboard
1. Navigate to **📊 Dashboard**
2. Select an account or view "All Accounts" for consolidated view
3. View KPIs and visualizations filtered by account
4. Monitor budget vs. actual spending

### 6. Manage Transactions
1. Navigate to **💳 Transactions**
2. Use filters (date, category, account) to find specific transactions
3. View which account each transaction belongs to
4. Bulk edit categories
5. Save edits as permanent rules

### 7. Configure Budgets
1. Navigate to **💰 Budgets**
2. Add category budget limits
3. View budget compliance on dashboard

### 5. Manage Accounts & Reconcile
1. Navigate to **🏦 Accounts**
2. Add your bank accounts with opening balances
3. Go to **⚖️ Reconciliation**
4. Compare app balance with bank statements
5. Detect duplicates and resolve variances
6. Mark transactions as reconciled

For detailed reconciliation instructions, see [Reconciliation Guide](docs/RECONCILIATION.md)

---

## 🔒 Security & Privacy

- ✅ **100% Local:** All data stays on your machine (no cloud uploads)
- ✅ **No External Connections:** App runs entirely offline
- ✅ **Docker Isolation:** Non-root user, containerized environment
- ✅ **Environment Variables:** Secrets managed via `.env` file

---

## 🐛 Troubleshooting

For detailed troubleshooting, see the **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)**.

**Quick Tips:**

**Port 8501 Already in Use:**
```bash
# Change port in docker-compose.yml
ports:
  - "8502:8501"  # Use 8502 instead
```

**PDF Parsing Issues:**
- See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed error messages and solutions
- Ensure PDF is machine-generated (not scanned image)
- Check if PDF has visible table structure
- Try exporting as CSV from your bank instead
- Enable DEBUG logging: `LOG_LEVEL=DEBUG` in `.env`

**Duplicate Detection Not Working:**
- Verify date formats are consistent across uploads
- Check if descriptions are exactly identical

---

## 📝 License

MIT License - See `LICENSE` file for details

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

---

## 📞 Support

For issues or questions:
- Open a GitHub issue
- Check documentation in `/docs`

---

**Built with ❤️ using Antigravity AI standards**

*Last updated: February 2026*
