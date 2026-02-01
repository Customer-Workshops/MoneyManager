"""
Report Generation Module for CashFlow-Local

Provides PDF, Excel/CSV, and JSON export functionality for financial reports.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from io import BytesIO
import json

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from src.database import db_manager

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generate financial reports in multiple formats (PDF, Excel, CSV, JSON).
    """
    
    def __init__(self):
        """Initialize the report generator."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for PDF reports."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2e5c8a'),
            spaceAfter=12
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#4a4a4a'),
            spaceAfter=6
        ))
    
    def get_transactions_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch transactions from database with optional filters.
        
        Args:
            start_date: Filter transactions after this date
            end_date: Filter transactions before this date
            category: Filter by category
            transaction_type: Filter by type (Credit/Debit)
        
        Returns:
            DataFrame with transaction data
        """
        query = "SELECT transaction_date, description, amount, type, category FROM transactions WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if transaction_type:
            query += " AND type = ?"
            params.append(transaction_type)
        
        query += " ORDER BY transaction_date DESC"
        
        try:
            with db_manager.get_connection() as conn:
                df = conn.execute(query, params).fetchdf()
                return df
        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}")
            return pd.DataFrame()
    
    def generate_monthly_statement_pdf(
        self,
        start_date: datetime,
        end_date: datetime,
        category: Optional[str] = None
    ) -> BytesIO:
        """
        Generate monthly statement PDF report.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            category: Optional category filter
        
        Returns:
            BytesIO object containing PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Title
        title = Paragraph("Monthly Financial Statement", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.2 * inch))
        
        # Date range
        date_range_text = f"Period: {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        if category:
            date_range_text += f" | Category: {category}"
        date_para = Paragraph(date_range_text, self.styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 0.3 * inch))
        
        # Fetch data
        df = self.get_transactions_data(start_date, end_date, category)
        
        if df.empty:
            story.append(Paragraph("No transactions found for this period.", self.styles['Normal']))
        else:
            # Summary section
            story.append(Paragraph("Summary", self.styles['CustomSubtitle']))
            
            total_income = df[df['type'] == 'Credit']['amount'].sum()
            total_expenses = df[df['type'] == 'Debit']['amount'].sum()
            net_cashflow = total_income - total_expenses
            
            summary_data = [
                ['Metric', 'Amount'],
                ['Total Income', f'${total_income:,.2f}'],
                ['Total Expenses', f'${total_expenses:,.2f}'],
                ['Net Cash Flow', f'${net_cashflow:,.2f}']
            ]
            
            summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.3 * inch))
            
            # Category breakdown
            story.append(Paragraph("Category Breakdown", self.styles['CustomSubtitle']))
            
            category_summary = df.groupby('category')['amount'].sum().reset_index()
            category_summary = category_summary.sort_values('amount', ascending=False)
            
            category_data = [['Category', 'Total Amount']]
            for _, row in category_summary.iterrows():
                category_data.append([row['category'], f"${row['amount']:,.2f}"])
            
            category_table = Table(category_data, colWidths=[3 * inch, 2 * inch])
            category_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e5c8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            story.append(category_table)
            story.append(Spacer(1, 0.3 * inch))
            
            # Top transactions
            story.append(Paragraph("Top 10 Transactions", self.styles['CustomSubtitle']))
            
            top_transactions = df.nlargest(10, 'amount')
            trans_data = [['Date', 'Description', 'Type', 'Amount']]
            
            for _, row in top_transactions.iterrows():
                trans_data.append([
                    row['transaction_date'].strftime('%Y-%m-%d'),
                    row['description'][:40] + ('...' if len(row['description']) > 40 else ''),
                    row['type'],
                    f"${row['amount']:,.2f}"
                ])
            
            trans_table = Table(trans_data, colWidths=[1 * inch, 3 * inch, 0.8 * inch, 1.2 * inch])
            trans_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e5c8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            story.append(trans_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def generate_tax_report_pdf(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> BytesIO:
        """
        Generate tax report PDF with tax-relevant categories.
        
        Args:
            start_date: Report start date (typically year start)
            end_date: Report end date (typically year end)
        
        Returns:
            BytesIO object containing PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Title
        title = Paragraph("Tax Report", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.2 * inch))
        
        # Date range
        date_range_text = f"Tax Year: {start_date.strftime('%Y')} ({start_date.strftime('%B %d')} - {end_date.strftime('%B %d')})"
        date_para = Paragraph(date_range_text, self.styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 0.3 * inch))
        
        # Fetch all transactions
        df = self.get_transactions_data(start_date, end_date)
        
        if df.empty:
            story.append(Paragraph("No transactions found for this period.", self.styles['Normal']))
        else:
            # Tax-relevant categories (common deductible categories)
            tax_categories = [
                'Business Expenses', 'Home Office', 'Medical', 'Charitable Donations',
                'Education', 'Professional Development', 'Office Supplies',
                'Travel', 'Insurance', 'Utilities'
            ]
            
            # Filter for tax-relevant transactions
            tax_df = df[df['category'].isin(tax_categories)]
            
            # Summary
            story.append(Paragraph("Deductible Expenses Summary", self.styles['CustomSubtitle']))
            
            total_deductible = tax_df['amount'].sum()
            
            summary_data = [
                ['Category', 'Total Amount', 'Count'],
            ]
            
            category_summary = tax_df.groupby('category').agg({
                'amount': ['sum', 'count']
            }).reset_index()
            category_summary.columns = ['Category', 'Total', 'Count']
            category_summary = category_summary.sort_values('Total', ascending=False)
            
            for _, row in category_summary.iterrows():
                summary_data.append([
                    row['Category'],
                    f"${row['Total']:,.2f}",
                    str(row['Count'])
                ])
            
            summary_data.append(['TOTAL DEDUCTIBLE', f"${total_deductible:,.2f}", ''])
            
            summary_table = Table(summary_data, colWidths=[3 * inch, 1.5 * inch, 1 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (2, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -2), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey]),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#2e5c8a')),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.3 * inch))
            
            # Detailed transactions by category
            story.append(Paragraph("Detailed Deductible Transactions", self.styles['CustomSubtitle']))
            story.append(Spacer(1, 0.1 * inch))
            
            for category in tax_df['category'].unique():
                cat_df = tax_df[tax_df['category'] == category]
                
                story.append(Paragraph(f"{category} ({len(cat_df)} transactions)", self.styles['SectionHeader']))
                
                trans_data = [['Date', 'Description', 'Amount']]
                for _, row in cat_df.iterrows():
                    trans_data.append([
                        row['transaction_date'].strftime('%Y-%m-%d'),
                        row['description'][:50] + ('...' if len(row['description']) > 50 else ''),
                        f"${row['amount']:,.2f}"
                    ])
                
                trans_table = Table(trans_data, colWidths=[1 * inch, 3.5 * inch, 1.5 * inch])
                trans_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                ]))
                story.append(trans_table)
                story.append(Spacer(1, 0.2 * inch))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def generate_category_report_pdf(
        self,
        start_date: datetime,
        end_date: datetime,
        category: str
    ) -> BytesIO:
        """
        Generate detailed category report PDF.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            category: Category to report on
        
        Returns:
            BytesIO object containing PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Title
        title = Paragraph(f"Category Report: {category}", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.2 * inch))
        
        # Date range
        date_range_text = f"Period: {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        date_para = Paragraph(date_range_text, self.styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 0.3 * inch))
        
        # Fetch data
        df = self.get_transactions_data(start_date, end_date, category)
        
        if df.empty:
            story.append(Paragraph(f"No transactions found for category '{category}' in this period.", self.styles['Normal']))
        else:
            # Summary
            story.append(Paragraph("Category Summary", self.styles['CustomSubtitle']))
            
            total_amount = df['amount'].sum()
            avg_amount = df['amount'].mean()
            transaction_count = len(df)
            
            summary_data = [
                ['Metric', 'Value'],
                ['Total Spent', f'${total_amount:,.2f}'],
                ['Average Transaction', f'${avg_amount:,.2f}'],
                ['Number of Transactions', str(transaction_count)],
            ]
            
            summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.3 * inch))
            
            # All transactions
            story.append(Paragraph("All Transactions", self.styles['CustomSubtitle']))
            
            trans_data = [['Date', 'Description', 'Type', 'Amount']]
            
            for _, row in df.iterrows():
                trans_data.append([
                    row['transaction_date'].strftime('%Y-%m-%d'),
                    row['description'][:40] + ('...' if len(row['description']) > 40 else ''),
                    row['type'],
                    f"${row['amount']:,.2f}"
                ])
            
            trans_table = Table(trans_data, colWidths=[1 * inch, 3 * inch, 0.8 * inch, 1.2 * inch])
            trans_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e5c8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            story.append(trans_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def generate_transaction_listing_pdf(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> BytesIO:
        """
        Generate transaction listing PDF with filters.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            category: Optional category filter
            transaction_type: Optional type filter (Credit/Debit)
        
        Returns:
            BytesIO object containing PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Title
        title = Paragraph("Transaction Listing", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.2 * inch))
        
        # Filters applied
        filters_text = "Filters: "
        if start_date and end_date:
            filters_text += f"Date: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} | "
        if category:
            filters_text += f"Category: {category} | "
        if transaction_type:
            filters_text += f"Type: {transaction_type} | "
        
        if filters_text == "Filters: ":
            filters_text = "No filters applied"
        else:
            filters_text = filters_text.rstrip(" | ")
        
        filters_para = Paragraph(filters_text, self.styles['Normal'])
        story.append(filters_para)
        story.append(Spacer(1, 0.3 * inch))
        
        # Fetch data
        df = self.get_transactions_data(start_date, end_date, category, transaction_type)
        
        if df.empty:
            story.append(Paragraph("No transactions found matching the filters.", self.styles['Normal']))
        else:
            # Summary
            story.append(Paragraph(f"Summary ({len(df)} transactions)", self.styles['CustomSubtitle']))
            
            total_credits = df[df['type'] == 'Credit']['amount'].sum()
            total_debits = df[df['type'] == 'Debit']['amount'].sum()
            
            summary_data = [
                ['Metric', 'Amount'],
                ['Total Credits', f'${total_credits:,.2f}'],
                ['Total Debits', f'${total_debits:,.2f}'],
                ['Net', f'${total_credits - total_debits:,.2f}']
            ]
            
            summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.3 * inch))
            
            # Transactions table
            story.append(Paragraph("Transactions", self.styles['CustomSubtitle']))
            
            trans_data = [['Date', 'Description', 'Category', 'Type', 'Amount']]
            
            for _, row in df.iterrows():
                trans_data.append([
                    row['transaction_date'].strftime('%Y-%m-%d'),
                    row['description'][:30] + ('...' if len(row['description']) > 30 else ''),
                    row['category'][:15] + ('...' if len(row['category']) > 15 else ''),
                    row['type'],
                    f"${row['amount']:,.2f}"
                ])
            
            trans_table = Table(trans_data, colWidths=[0.9 * inch, 2.2 * inch, 1.2 * inch, 0.7 * inch, 1 * inch])
            trans_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e5c8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            story.append(trans_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def export_to_excel(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> BytesIO:
        """
        Export transactions to Excel format.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            category: Optional category filter
            transaction_type: Optional type filter (Credit/Debit)
        
        Returns:
            BytesIO object containing Excel data
        """
        df = self.get_transactions_data(start_date, end_date, category, transaction_type)
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Main transactions sheet
            df.to_excel(writer, sheet_name='Transactions', index=False)
            
            # Summary sheet
            if not df.empty:
                summary_data = {
                    'Metric': ['Total Credits', 'Total Debits', 'Net Cash Flow', 'Transaction Count'],
                    'Value': [
                        df[df['type'] == 'Credit']['amount'].sum(),
                        df[df['type'] == 'Debit']['amount'].sum(),
                        df[df['type'] == 'Credit']['amount'].sum() - df[df['type'] == 'Debit']['amount'].sum(),
                        len(df)
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Category breakdown sheet
                category_summary = df.groupby('category')['amount'].sum().reset_index()
                category_summary.columns = ['Category', 'Total Amount']
                category_summary = category_summary.sort_values('Total Amount', ascending=False)
                category_summary.to_excel(writer, sheet_name='Category Breakdown', index=False)
        
        buffer.seek(0)
        return buffer
    
    def export_to_csv(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> BytesIO:
        """
        Export transactions to CSV format.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            category: Optional category filter
            transaction_type: Optional type filter (Credit/Debit)
        
        Returns:
            BytesIO object containing CSV data
        """
        df = self.get_transactions_data(start_date, end_date, category, transaction_type)
        
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return buffer
    
    def export_to_json(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> BytesIO:
        """
        Export transactions to JSON format for backup and data portability.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            category: Optional category filter
            transaction_type: Optional type filter (Credit/Debit)
        
        Returns:
            BytesIO object containing JSON data
        """
        df = self.get_transactions_data(start_date, end_date, category, transaction_type)
        
        # Convert DataFrame to JSON
        json_data = df.to_dict(orient='records')
        
        # Convert datetime objects to strings
        for record in json_data:
            if 'transaction_date' in record and hasattr(record['transaction_date'], 'strftime'):
                record['transaction_date'] = record['transaction_date'].strftime('%Y-%m-%d')
        
        buffer = BytesIO()
        buffer.write(json.dumps(json_data, indent=2).encode('utf-8'))
        buffer.seek(0)
        return buffer


# Global instance
report_generator = ReportGenerator()
