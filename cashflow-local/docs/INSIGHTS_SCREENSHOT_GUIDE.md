# AI Insights Dashboard - Visual Guide

## Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🤖 AI-Powered Smart Insights                                   │
│  Get personalized financial insights and actionable             │
│  recommendations                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  💯 Financial Health Score                                      │
│  ┌─────────────────┬─────────────────────────────────────────┐ │
│  │                 │  Score Breakdown                         │ │
│  │      75         │  Savings Rate: 30/40 ████████░░         │ │
│  │   Grade: C      │  Savings rate: 15.0%                    │ │
│  │  Good progress! │                                         │ │
│  │  Keep improving │  Budget Adherence: 24/30 ████████░      │ │
│  │                 │  2/3 budgets on track                   │ │
│  │                 │                                         │ │
│  │                 │  Spending Stability: 21/30 ███████░     │ │
│  │                 │  Spending variability: 12.3%            │ │
│  └─────────────────┴─────────────────────────────────────────┘ │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  💡 Top 3 Actionable Tips                                       │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────┐ │
│  │ ⚠️ You're on    │ │ 📈 Your Dining  │ │ 💡 Recurring   │ │
│  │ track to exceed │ │ spending         │ │ charge:        │ │
│  │ dining budget   │ │ increased by 25% │ │ NETFLIX costs  │ │
│  │ (currently at   │ │ over 3 months    │ │ $16/month      │ │
│  │ 92%)            │ │                  │ │ Consider       │ │
│  │                 │ │                  │ │ reviewing      │ │
│  └──────────────────┘ └──────────────────┘ └────────────────┘ │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📊 Spending Analysis │ 📈 Trends │ 🔮 Predictions │ ... │     │
│  ────────────────────────────────────────────────────────────   │
│                                                                  │
│  ⚠️ Budget Alerts                                               │
│  🔴 Dining - 92% used                                           │
│  ├─ Budget Limit: $500.00                                       │
│  ├─ Current Spending: $460.00                                   │
│  ├─ Usage: 92.0%                                                │
│  └─ Remaining: $40.00                                           │
│     💡 You're on track to exceed dining budget (currently at    │
│        92%)                                                      │
│                                                                  │
│  🟡 Groceries - 75% used                                        │
│  ├─ Budget Limit: $400.00                                       │
│  ├─ Current Spending: $300.00                                   │
│  ├─ Usage: 75.0%                                                │
│  └─ Remaining: $100.00                                          │
│     ⚡ You've used 75.0% of your Groceries budget               │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  🔍 Spending Anomalies                                          │
│  Unusual spending patterns compared to your historical average  │
│                                                                  │
│  🔴 Dining                                                       │
│  ├─ Current Month: $450.00                                      │
│  ├─ Historical Average: $300.00                                 │
│  └─ Change: +50.0%                                              │
│     ⚠️ You spent 50% MORE on Dining this month ($450)          │
│                                                                  │
│  🟡 Entertainment                                                │
│  ├─ Current Month: $80.00                                       │
│  ├─ Historical Average: $120.00                                 │
│  └─ Change: -33.3%                                              │
│     ✅ You spent 33% LESS on Entertainment this month ($80)    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Tabs Overview

### 📊 Spending Analysis Tab
- Budget alerts (critical/warning)
- Spending anomalies detected by Z-score analysis
- Color-coded severity indicators

### 📈 Trends Tab
- 3-month spending trends
- Category-wise increase/decrease percentages
- Visual trend indicators (📈 up, 📉 down)

### 🔮 Predictions Tab
- End-of-month spending forecasts
- Table showing spent vs projected amounts
- Days remaining in month

### 💰 Savings Tab
- Recurring subscription analysis
- High-spending categories
- Potential monthly savings total

### 🔁 Patterns Tab
- Recurring transactions list
- Potential duplicate charges
- Suggestions for automation

## Color Scheme

- 🟢 Green: Good (< 70% budget usage, positive savings)
- 🟡 Yellow: Warning (70-90% budget usage, moderate concerns)
- 🔴 Red: Critical (> 90% budget usage, immediate attention needed)

## Interactive Elements

- **Expandable Cards**: Click to see detailed breakdowns
- **Progress Bars**: Visual representation of budget usage
- **Tabs**: Switch between insight categories
- **Metrics**: Large numbers for quick scanning
- **Icons**: Quick visual indicators (⚠️, ✅, 💡, etc.)

## Data Refresh

- Insights update automatically when new transactions are uploaded
- Financial Health Score recalculates with each page load
- All statistics are computed on-demand from DuckDB
