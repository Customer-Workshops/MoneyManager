"""
Test script to debug PDF parsing on the actual test file.
"""
import sys
sys.path.insert(0, '/app')

from src.parsers import PDFParser
import logging

# Configure logging to see all messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_pdf(pdf_path):
    print(f"\n{'='*60}")
    print(f"Testing PDF Parser: {pdf_path}")
    print(f"{'='*60}\n")
    
    try:
        parser = PDFParser(pdf_path)
        df = parser.parse()
        
        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}")
        print(f"Total transactions parsed: {len(df)}")
        
        if not df.empty:
            print(f"\nColumns: {list(df.columns)}")
            print(f"\nDataFrame shape: {df.shape}")
            print(f"\nFirst 5 transactions:")
            print(df.head().to_string())
            print(f"\nData types:")
            print(df.dtypes)
        else:
            print("\n⚠️  DataFrame is EMPTY!")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf("/app/data/test_statement.pdf")
