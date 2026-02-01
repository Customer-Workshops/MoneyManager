"""
Debug script to test PDF parsing with pdfplumber.
This will show exactly what tables and columns are extracted.
"""

import pdfplumber
import pandas as pd
import sys

def debug_pdf(pdf_path):
    """Debug PDF extraction to see raw table structure."""
    
    print(f"\n{'='*60}")
    print(f"PDF DEBUG ANALYSIS: {pdf_path}")
    print(f"{'='*60}\n")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📄 Total Pages: {len(pdf.pages)}\n")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n{'─'*60}")
                print(f"Page {page_num}")
                print(f"{'─'*60}")
                
                tables = page.extract_tables()
                
                if not tables:
                    print(f"  ❌ No tables found on this page")
                    continue
                
                print(f"  ✅ Found {len(tables)} table(s)")
                
                for table_idx, table in enumerate(tables, 1):
                    print(f"\n  Table {table_idx}:")
                    print(f"    Rows: {len(table)}")
                    
                    if len(table) < 2:
                        print(f"    ⚠️  Too few rows, skipping")
                        continue
                    
                    # Show header row
                    print(f"\n    Header Row (raw):")
                    print(f"      {table[0]}")
                    
                    # Clean headers
                    cleaned_headers = [str(cell).strip() if cell is not None else '' for cell in table[0]]
                    print(f"\n    Cleaned Headers:")
                    for i, header in enumerate(cleaned_headers):
                        print(f"      [{i}] '{header}'")
                    
                    # Show first data row
                    if len(table) > 1:
                        print(f"\n    First Data Row (raw):")
                        print(f"      {table[1]}")
                    
                    # Try to create DataFrame
                    try:
                        # Clean table
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [str(cell).strip() if cell is not None else '' for cell in row]
                            if any(cell for cell in cleaned_row):
                                cleaned_table.append(cleaned_row)
                        
                        if len(cleaned_table) >= 2:
                            df = pd.DataFrame(cleaned_table[1:], columns=cleaned_table[0])
                            print(f"\n    DataFrame Info:")
                            print(f"      Shape: {df.shape}")
                            print(f"      Columns (lowercase):")
                            for col in df.columns:
                                print(f"        - '{col}' → lowercase: '{col.lower()}'")
                            
                            print(f"\n    Sample Data (first 3 rows):")
                            print(df.head(3).to_string(index=False))
                    
                    except Exception as e:
                        print(f"    ❌ Failed to create DataFrame: {e}")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_pdf.py <path_to_pdf>")
        sys.exit(1)
    
    debug_pdf(sys.argv[1])
