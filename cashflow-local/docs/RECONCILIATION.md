# Bank Account Reconciliation & Balance Tracking Feature

## Overview

The Bank Account Reconciliation & Balance Tracking feature helps users ensure their app data matches their actual bank balance. It provides tools for reconciliation, duplicate detection, variance analysis, and balance history tracking.

## Features Implemented

### 1. Account Management (🏦 Accounts Page)

**Location:** Navigation → 🏦 Accounts

**Capabilities:**
- Create multiple bank accounts with unique names
- Set opening balances and opening balance dates
- Support for different account types (Checking, Savings, Credit Card, Investment, Other)
- Multi-currency support (INR, USD, EUR, GBP, JPY)
- Calculate current balance based on transactions
- View account details and status

**How to Use:**
1. Navigate to the **🏦 Accounts** page
2. Click on the **➕ Add Account** tab
3. Fill in the account details:
   - Account Name (required, must be unique)
   - Account Type
   - Opening Balance
   - Opening Balance Date
   - Currency
4. Click **➕ Add Account** to save

### 2. Balance Reconciliation (⚖️ Reconciliation Page)

**Location:** Navigation → ⚖️ Reconciliation

The reconciliation page provides four main features organized in tabs:

#### Tab 1: 🔍 Reconcile Balance

**Purpose:** Compare your app balance with your actual bank statement

**Workflow:**
1. Select an account from the dropdown
2. Enter the **Statement Date** (the date on your bank statement)
3. Enter the **Statement Balance** (the balance shown on your bank statement)
4. Click **🔍 Analyze Balance**

**Results:**
- **App Balance**: Calculated balance from transactions
- **Bank Statement**: Balance from your bank statement
- **Variance**: Difference between the two balances
- **Status**: ✅ Reconciled or ⚠️ Variance Detected
- **Suggestions**: Recommendations for missing transactions
- **Unreconciled Transactions**: List of transactions not yet reconciled

**Actions:**
- **Mark All as Reconciled**: Bulk reconcile all unreconciled transactions

#### Tab 2: 📊 Balance History

**Purpose:** Visualize balance trends over time

**Features:**
- Interactive timeline chart showing:
  - App-calculated balance (solid line)
  - Bank statement balance (dashed line)
- Variance details table with reconciliation status
- Date range selector for custom periods

**How to Use:**
1. Select an account
2. Choose date range (From/To dates)
3. View the balance timeline chart and variance details

#### Tab 3: 🔄 Duplicate Detection

**Purpose:** Find potential duplicate transactions

**Parameters:**
- **Date Threshold**: Number of days to consider for duplicates (1-7 days)
- **Amount Tolerance**: Acceptable difference in amounts (₹0.01)

**Features:**
- Analyzes transactions for potential duplicates based on:
  - Same or similar amount
  - Similar description (70%+ similarity)
  - Within specified date threshold
- Shows side-by-side comparison of potential duplicates
- Displays similarity percentage and analysis metrics

**How to Use:**
1. Select an account
2. Adjust detection parameters if needed
3. Click **🔍 Detect Duplicates**
4. Review potential duplicate pairs

#### Tab 4: 📋 Reconciliation Report

**Purpose:** Generate comprehensive reconciliation reports

**Report Contents:**
- **Summary Metrics:**
  - Opening Balance
  - Closing Balance
  - Net Change
  - Reconciliation Percentage
- **Transaction Breakdown:**
  - Total Transactions
  - Reconciled Count
  - Unreconciled Count
- **Unreconciled Transactions List**

**Export:**
- Download report as CSV file

**How to Use:**
1. Select an account
2. Choose date range for the report period
3. Click **📋 Generate Report**
4. Download CSV if needed

## Database Schema

### New Tables

#### `accounts` Table
Stores bank account information:
- `id`: Unique account identifier
- `name`: Account name (unique)
- `account_number`: Account number for reference
- `account_type`: Type of account (Checking, Savings, etc.)
- `opening_balance`: Initial balance
- `opening_balance_date`: Date of opening balance
- `currency`: Account currency (INR, USD, etc.)
- `is_active`: Account status (active/inactive)
- `created_at`: Creation timestamp

#### `account_balances` Table
Tracks balance history and reconciliation snapshots:
- `id`: Unique snapshot identifier
- `account_id`: Reference to account
- `balance_date`: Date of the snapshot
- `calculated_balance`: App-calculated balance
- `actual_balance`: User-entered bank balance
- `variance`: Difference between calculated and actual
- `is_reconciled`: Whether balances match (variance < ₹0.01)
- `reconciled_at`: Reconciliation timestamp
- `notes`: Optional notes
- `created_at`: Creation timestamp

### Modified Tables

#### `transactions` Table (New Fields)
- `account_id`: Link transaction to specific account
- `reconciled`: Boolean flag for reconciliation status
- `reconciled_at`: Timestamp of reconciliation

## Backend Modules

### `src/database.py` (Enhanced)

**New Methods:**
- `get_accounts(active_only=True)`: Retrieve all accounts
- `get_account_by_id(account_id)`: Get specific account
- `calculate_account_balance(account_id, as_of_date)`: Calculate balance
- `mark_transactions_reconciled(transaction_ids, reconciled)`: Mark transactions
- `save_balance_snapshot(...)`: Save balance reconciliation snapshot
- `get_balance_history(account_id, start_date, end_date)`: Get balance snapshots

### `src/reconciliation.py` (New)

**ReconciliationEngine Class:**
- `detect_duplicates(account_id, threshold_days, amount_tolerance)`: Find duplicate transactions
- `analyze_variance(account_id, statement_date, statement_balance)`: Compare balances
- `suggest_missing_transactions(...)`: Suggest missing transactions based on balance gap
- `generate_reconciliation_report(...)`: Create comprehensive reconciliation report

## Testing

### Test Suite: `tests/test_reconciliation.py`

**Test Coverage:**
- Account creation and retrieval
- Balance calculation with opening balance and transactions
- Balance calculation as of specific dates
- Transaction reconciliation marking
- Balance snapshot creation
- Variance detection
- Duplicate transaction detection
- Missing transaction suggestions
- Reconciliation report generation
- Balance history retrieval with filters

**Run Tests:**
```bash
pytest tests/test_reconciliation.py -v
```

## Usage Examples

### Example 1: Monthly Reconciliation

1. **Prepare Your Bank Statement:**
   - Obtain your bank statement for the month
   - Note the ending balance and date

2. **Reconcile in App:**
   ```
   Navigate to: ⚖️ Reconciliation → 🔍 Reconcile Balance
   
   Select Account: "HDFC Savings"
   Statement Date: 2025-01-31
   Statement Balance: ₹45,327.50
   
   Click: 🔍 Analyze Balance
   ```

3. **Review Results:**
   - If variance found, review suggested missing transactions
   - Check unreconciled transactions list
   - Mark verified transactions as reconciled

4. **Complete Reconciliation:**
   - Click "Mark All as Reconciled" when satisfied
   - Balance snapshot saved automatically

### Example 2: Find Duplicate Transactions

```
Navigate to: ⚖️ Reconciliation → 🔄 Duplicate Detection

Select Account: "HDFC Savings"
Date Threshold: 3 days
Amount Tolerance: ₹0.01

Click: 🔍 Detect Duplicates

Review potential duplicates and delete if confirmed
```

### Example 3: Track Balance History

```
Navigate to: ⚖️ Reconciliation → 📊 Balance History

Select Account: "HDFC Savings"
From Date: 2025-01-01
To Date: 2025-03-31

View timeline chart showing balance trends
```

## Best Practices

1. **Regular Reconciliation:**
   - Reconcile monthly when you receive bank statements
   - More frequent reconciliation helps catch errors early

2. **Account Setup:**
   - Set accurate opening balances and dates
   - Link all transactions to appropriate accounts

3. **Transaction Assignment:**
   - Assign account when uploading statements
   - Update existing transactions to link them to accounts

4. **Variance Investigation:**
   - Investigate variances immediately
   - Common causes: missing transactions, incorrect amounts, duplicate entries
   - Use suggestions to identify likely issues

5. **Duplicate Prevention:**
   - Run duplicate detection before uploading new statements
   - Review potential duplicates carefully before deletion
   - The deduplication hash should prevent most duplicates

## Troubleshooting

### Variance in Balance

**Problem:** App balance doesn't match bank statement

**Solutions:**
1. Check for missing transactions using suggestions
2. Run duplicate detection to find accidental duplicates
3. Verify transaction types (Credit/Debit) are correct
4. Ensure opening balance and opening date are accurate
5. Check that all transactions are assigned to correct account

### No Accounts Available

**Problem:** "No accounts found" message on reconciliation page

**Solution:**
1. Navigate to 🏦 Accounts page
2. Add at least one account with opening balance
3. Return to reconciliation page

### Transactions Not Showing Up

**Problem:** Transactions don't appear in account balance calculation

**Solution:**
1. Check if transactions have `account_id` assigned
2. Update transactions in 💳 Transactions page to link to account
3. Verify transaction dates are after opening balance date

### Duplicate Detection Not Finding Duplicates

**Problem:** Known duplicates not detected

**Solution:**
1. Increase Date Threshold (try 7 days)
2. Increase Amount Tolerance if amounts differ slightly
3. Check if descriptions are too different (< 70% similarity)

## Future Enhancements

Potential improvements for future versions:

1. **Automated Bank Sync:**
   - Direct API integration with banks
   - Automatic transaction import
   - Real-time balance updates

2. **Smart Categorization:**
   - ML-based transaction categorization
   - Learning from user corrections

3. **Advanced Reporting:**
   - Detailed analytics and insights
   - Budget vs. actual comparisons
   - Cash flow forecasting

4. **Multi-Account Views:**
   - Consolidated view of all accounts
   - Cross-account transfers tracking
   - Net worth calculation

5. **Mobile App:**
   - Mobile-friendly reconciliation interface
   - Push notifications for variances
   - Photo capture of paper statements

## Security & Privacy

- **Local Storage:** All data stored locally in DuckDB
- **No Cloud Sync:** Data never leaves your machine
- **Docker Isolation:** Containerized for security
- **No External APIs:** Fully offline operation

## Support

For issues or questions:
1. Check the [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
2. Review test cases for usage examples
3. Open a GitHub issue with details

---

**Version:** 1.0.0
**Last Updated:** February 2026
**Author:** Antigravity AI
