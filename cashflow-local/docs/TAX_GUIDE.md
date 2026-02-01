# Tax Management Guide for CashFlow-Local

## Overview

CashFlow-Local now includes comprehensive tax category tagging and ITR filing support, specifically designed for Indian taxpayers. This feature helps you track tax-deductible expenses throughout the financial year and generate reports for ITR filing.

## Supported Tax Categories

### Section 80C - Investments (Limit: ₹1,50,000)
Deductions for investments in:
- ELSS (Equity Linked Savings Scheme)
- EPF (Employee Provident Fund)
- PPF (Public Provident Fund)
- Life Insurance Premiums
- Tax-saving Fixed Deposits
- NSC (National Savings Certificates)
- ULIP (Unit Linked Insurance Plan)
- Sukanya Samriddhi Yojana
- Senior Citizen Savings Scheme (SCSS)

### Section 80D - Health Insurance

**Standard (Limit: ₹25,000)**
- Health insurance premiums for self, spouse, and children
- Preventive health checkups (up to ₹5,000 within the ₹25,000 limit)

**Senior Citizens (Limit: ₹50,000)**
- Health insurance for parents who are senior citizens (60+ years)
- Medical expenses for senior citizen parents (if no insurance)

### Section 80E - Education Loan Interest (No Limit)
- Interest paid on education loans
- Applicable for loans taken for higher education
- Deduction available for 8 years or until interest is fully paid

### Section 80G - Donations to Charity
- Donations to eligible charitable institutions
- 50% or 100% deduction depending on the institution
- Donations to PM CARES Fund, CM Relief Fund, etc.

### Section 80TTA - Savings Account Interest (Limit: ₹10,000)
- Interest earned on savings accounts
- Applicable for individuals and HUFs
- Available for interest from banks, co-operative banks, and post offices

### HRA - House Rent Allowance
- Rent paid for residential accommodation
- Subject to specific calculation rules based on salary and rent
- Not applicable if you own a house in the same city

### Section 24 - Home Loan Interest (Limit: ₹2,00,000)
- Interest paid on home loan for self-occupied property
- Interest on loan for let-out property (no limit)
- Principal repayment qualifies under Section 80C

### Business Expenses
- Eligible expenses for self-employed/freelancers
- Office rent, utilities, equipment
- Professional fees and subscriptions
- Travel and other business-related costs

## How to Use Tax Features

### 1. Tag Transactions with Tax Categories

1. Navigate to **📋 Tax Reports** page
2. Click on **🏷️ Tag Transactions** tab
3. Select the financial year date range (April - March)
4. Browse through your transactions
5. For each tax-deductible transaction:
   - Use the multi-select dropdown to choose relevant tax categories
   - You can assign multiple categories if applicable
   - Click **💾 Save Tags** to save your selections

**Example:**
- A health insurance premium could be tagged with "80D - Health Insurance"
- An LIC premium could be tagged with "80C - Investments"
- A donation receipt could be tagged with "80G - Donations"

### 2. Monitor Tax Savings Dashboard

The **📊 Tax Summary** tab provides:

- **Total Deductions YTD:** Sum of all tagged tax-deductible expenses
- **Estimated Tax Savings:** Calculated at 30% tax bracket
- **Category-wise Utilization:** Progress bars showing usage vs. limits
- **Color-coded Alerts:**
  - 🟢 Green: < 70% of limit used (plenty of room)
  - 🟡 Yellow: 70-90% of limit used (approaching limit)
  - 🔴 Red: > 90% of limit used (near/exceeded limit)

### 3. View Category Details

The **📈 Category Details** tab allows you to:

1. Select a specific tax category
2. View all transactions tagged with that category
3. See total amount and utilization percentage
4. Analyze transaction-by-transaction breakdown

### 4. Export Reports for ITR Filing

The **📥 Export Reports** tab enables you to:

1. Select your financial year (defaults to current FY)
2. Click **📊 Export Summary to Excel**
3. Download an Excel file containing:
   - Summary sheet with all tax categories
   - Individual sheets for each tax section with detailed transactions
   - Ready to share with your CA or use for self-filing

### 5. Dashboard Widget

The main dashboard now includes a **💰 Tax Savings** widget showing:
- Total deductions for current FY
- Estimated tax savings
- Top 3 tax categories with utilization bars
- Quick link to detailed tax reports

## Best Practices

### 1. Tag Regularly
- Don't wait until March to tag transactions
- Tag expenses as you upload bank statements
- Review and tag monthly for better accuracy

### 2. Keep Supporting Documents
- While the app tracks amounts, maintain physical/digital copies of:
  - Insurance premium receipts
  - Investment certificates
  - Donation receipts
  - Rent receipts
  - Home loan statements

### 3. Multi-tagging Strategy
Use multiple tags when applicable:
- Rent payment → Both "HRA" and "Business Expenses" (if home office)
- Health checkup → "80D - Health Insurance" (within preventive checkup limits)

### 4. Review Before Filing
Before filing ITR:
1. Export the full tax report
2. Cross-verify with actual receipts
3. Check for any missed deductions
4. Ensure amounts are within limits
5. Share with CA or use for self-filing

### 5. Financial Year Awareness
- Indian FY runs from April 1 to March 31
- The app automatically detects current FY
- You can manually select previous FY for amendments

## Tax Planning Tips

### Maximize 80C (₹1.5L limit)
- Start early in the financial year
- Consider PPF for long-term savings
- ELSS funds offer tax benefits + growth potential
- Life insurance for protection + tax benefit

### Health Insurance (80D)
- Cover entire family under one policy for efficiency
- Senior citizen parents qualify for higher limits
- Preventive health checkups count toward the limit

### Save Throughout the Year
- Set aside monthly amounts for tax-saving investments
- Use the dashboard widget to track progress
- Avoid last-minute rush in March

### Document Everything
- Scan and store all receipts
- Maintain digital copies of certificates
- Keep transaction records for 7 years (as per IT rules)

## Limitations & Disclaimers

⚠️ **Important Notes:**

1. **Tax Calculation:** The estimated savings are based on a 30% tax bracket assumption. Your actual tax liability depends on your total income and applicable tax slab.

2. **Not Financial Advice:** This tool helps organize tax data but does not provide tax advice. Consult a qualified CA or tax advisor.

3. **Manual Verification Required:** Always verify totals and eligibility with official IT department guidelines.

4. **Rules Change:** Tax laws are subject to change. Verify current limits and rules during ITR filing.

5. **Self-responsibility:** Users are responsible for accurate tagging and reporting of tax deductions.

## Troubleshooting

### Transactions not appearing in tax summary?
- Ensure transactions are properly tagged
- Check if date range includes the transaction date
- Verify the financial year selection

### Excel export not working?
- Ensure xlsxwriter package is installed
- Check browser download settings
- Try a different browser if issues persist

### Can't remove a tax tag?
- Click the tag in the multi-select dropdown to deselect
- Click "Save Tags" to apply the change

### Utilization showing as "N/A"?
- Some categories (80E, 80G) have no fixed limits
- Utilization percentage is only calculated for categories with limits

## Support & Feedback

For issues or feature requests related to tax management:
1. Check this documentation
2. Review the main README.md
3. Open a GitHub issue with details
4. Tag issues with "tax-features" label

---

**Disclaimer:** This software is provided as-is for personal financial tracking. Always consult with a qualified tax professional for tax planning and ITR filing decisions. The developers are not responsible for any tax-related errors or omissions.

**Last Updated:** February 2026
