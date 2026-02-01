# PDF Parser Troubleshooting Guide

## Common Issues and Solutions

### ❌ "PDF file not found"

**Error Message:**
```
PDF file not found: /path/to/file.pdf
💡 Tip: Check the file path and ensure the file exists
```

**Solution:**
- Verify the file path is correct
- Ensure the file exists in the specified location
- Check file permissions

---

### ❌ "No transaction table found"

**Error Message:**
```
❌ Failed to parse PDF: No transaction table found
💡 Tip: Make sure this is a bank statement PDF with a transaction table
```

**Possible Causes:**
1. PDF is scanned/image-based (not machine-readable text)
2. PDF is encrypted/password-protected
3. PDF doesn't contain a transaction table

**Solutions:**
- Ensure the PDF is a machine-generated bank statement (not a scanned image)
- If the PDF is password-protected, unlock it first
- Try exporting the statement as CSV from your bank's website instead
- Check if the PDF contains visible transaction tables

---

### ❌ "No header row with 'Date' found"

**Error Message:**
```
❌ Failed to parse PDF: No header row with 'Date' found
💡 Tip: This PDF may not be in a supported bank statement format
```

**Possible Causes:**
1. Non-standard bank statement format
2. PDF doesn't have a recognizable date column header

**Solutions:**
- Verify the PDF is a standard bank statement
- Check if the transaction table has a "Date" column header
- Try exporting as CSV if available

---

### ⚠️ "Parsed 0 transactions"

**Error Message:**
```
⚠️ Parsed 0 transactions (all rows filtered out)
💡 Tip: Check if the PDF contains valid transaction dates in supported formats (DD/MM/YYYY, DD-MM-YYYY)
```

**Possible Causes:**
1. Date format not recognized
2. All transactions have zero amounts
3. Transaction rows don't contain valid dates

**Solutions:**
- Check the date format in your PDF (supported: DD/MM/YYYY, DD-MM-YYYY, DD-MMM-YYYY)
- Ensure transactions have non-zero amounts
- Verify the PDF contains actual transaction data

---

## CSV Parser Issues

### ❌ "Missing required column: Date"

**Error Message:**
```
❌ Missing required column: Date
💡 CSV columns found: Transaction ID, Memo, Amount
💡 Expected one of: date, trans date, transaction date, posted date
```

**Solution:**
- Ensure your CSV has a date column with a recognizable name
- Supported column names: Date, Trans Date, Transaction Date, Posted Date, Posting Date, Value Date

---

### ❌ "Missing required column: Description"

**Error Message:**
```
❌ Missing required column: Description
💡 CSV columns found: Date, Amount, Type
💡 Expected one of: description, memo, details, merchant, name, payee, particulars
```

**Solution:**
- Ensure your CSV has a description/memo column
- Supported column names: Description, Memo, Details, Merchant, Name, Payee, Particulars

---

### ❌ "Missing amount columns"

**Error Message:**
```
❌ Missing amount columns (debit/credit)
💡 CSV columns found: Date, Description
💡 Expected debit or credit column
```

**Solution:**
- Ensure your CSV has amount columns
- Supported formats:
  - Separate Debit/Credit columns
  - Single Amount column (positive for credit, negative for debit)

---

## Supported Formats

### Date Formats

The parser supports the following date formats:
- `DD/MM/YYYY` - e.g., 01/09/2025
- `DD-MM-YYYY` - e.g., 01-09-2025
- `DD-MMM-YYYY` - e.g., 01-Sep-2025
- `DD MMM YYYY` - e.g., 01 Sep 2025
- `YYYY-MM-DD` - e.g., 2025-09-01
- `DD.MM.YYYY` - e.g., 01.09.2025
- `DD/MM/YY` - e.g., 01/09/25

**Note:** For CSV files, use consistent date formats throughout the file for best results.

---

### Amount Formats

The parser supports various amount formats:

| Format | Example | Parsed Value |
|--------|---------|--------------|
| Plain | `1234.56` | 1234.56 |
| Comma-separated | `1,234.56` | 1234.56 |
| Currency symbols | `₹1,234.56` | 1234.56 |
| No decimals | `500` | 500.0 |
| Accounting format | `(1234.56)` | -1234.56 |
| Debit indicators | `1234.56 Dr` | 1234.56 |
| Credit indicators | `1234.56 Cr` | 1234.56 |
| Empty/placeholder | `--`, `-`, empty | None (filtered out) |

---

### Bank Statement Formats

#### Currently Tested

- ✅ **Federal Bank** - Multi-column format with split headers

#### Expected to Work

Most Indian bank statements with standard tabular formats should work if they have:
- A header row containing "Date"
- A description/particulars column
- Debit and/or Credit amount columns
- Dates in supported formats

#### Known Limitations

- ❌ Scanned PDFs (image-based) - Not supported
- ❌ Password-protected PDFs - Must be unlocked first
- ❌ Handwritten statements - Not supported
- ⚠️ Custom bank formats - May require column mapping adjustments

---

## Performance Tips

### Large Statements

The parser can handle large statements (1000+ transactions):
- PDFs are processed page-by-page to avoid memory issues
- CSV files are loaded efficiently with pandas
- Expected processing time: < 3 seconds for 100 pages

### Optimization

If you're processing many statements:
1. Use CSV format when available (faster than PDF)
2. Ensure PDFs are machine-generated (not scanned)
3. Process statements sequentially rather than in parallel

---

## Getting Help

If you encounter an issue not covered here:

1. **Check the logs** - Enable DEBUG logging to see detailed parsing information
2. **Try CSV export** - If PDF parsing fails, try exporting as CSV from your bank
3. **Report the issue** - Include:
   - Error message (full text)
   - Bank name and statement type
   - Sample PDF structure (anonymized)
   - Expected vs. actual behavior

---

## Diagnostic Mode

Enable detailed logging to troubleshoot parsing issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show:
- Detected columns and mappings
- Number of rows extracted
- Filtering steps and results
- Any warnings or errors during parsing

---

## Best Practices

### For Best Results

1. **Use machine-generated PDFs** from your bank's website
2. **Keep date formats consistent** within a single file
3. **Verify the PDF structure** - should have a clear transaction table
4. **Check for password protection** - unlock PDFs before parsing
5. **Use CSV when available** - faster and more reliable than PDF

### Data Quality

To ensure accurate parsing:
- Review the first few transactions after parsing
- Check that dates are interpreted correctly (DD/MM vs MM/DD)
- Verify amounts match your statement
- Ensure debit/credit classification is correct

---

*Last updated: February 2026*
