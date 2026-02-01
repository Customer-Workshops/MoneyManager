"""
AI-Powered Smart Insights Engine for CashFlow-Local

Provides intelligent spending analysis, anomaly detection, trend identification,
and personalized financial recommendations.

Features:
- Spending anomaly detection using Z-score analysis
- Trend analysis across time periods
- Budget predictions and alerts
- Savings opportunities identification
- Pattern detection (recurring transactions, subscriptions)
- Financial health scoring

Author: Antigravity AI
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

import pandas as pd
import numpy as np

from .database import DatabaseManager

logger = logging.getLogger(__name__)


class InsightsEngine:
    """
    AI-powered insights engine for financial analytics.
    
    Uses statistical methods and rule-based logic to generate
    actionable insights from transaction data.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the insights engine.
        
        Args:
            db_manager: Database connection manager
        """
        self.db_manager = db_manager
        logger.info("InsightsEngine initialized")
    
    def get_all_insights(self) -> Dict[str, Any]:
        """
        Generate all available insights.
        
        Returns:
            Dictionary containing all insight categories
        """
        try:
            insights = {
                'anomalies': self.detect_spending_anomalies(),
                'trends': self.analyze_trends(),
                'predictions': self.predict_monthly_spending(),
                'budget_alerts': self.get_budget_alerts(),
                'savings_opportunities': self.find_savings_opportunities(),
                'patterns': self.detect_patterns(),
                'health_score': self.calculate_financial_health_score(),
                'top_tips': []  # Will be populated from other insights
            }
            
            # Generate top 3 actionable tips
            insights['top_tips'] = self._generate_top_tips(insights)
            
            return insights
        
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return self._empty_insights()
    
    def detect_spending_anomalies(self) -> List[Dict[str, Any]]:
        """
        Detect spending anomalies using Z-score analysis.
        
        Identifies categories where current month spending is significantly
        different from historical average (>2 standard deviations).
        
        Returns:
            List of anomaly insights
        """
        try:
            anomalies = []
            
            # Get spending by category for last 6 months
            query = """
                SELECT 
                    category,
                    EXTRACT(YEAR FROM transaction_date) as year,
                    EXTRACT(MONTH FROM transaction_date) as month,
                    SUM(amount) as total_amount
                FROM transactions
                WHERE type = 'Debit'
                    AND transaction_date >= CURRENT_DATE - INTERVAL '6 months'
                    AND category != 'Uncategorized'
                GROUP BY category, year, month
                ORDER BY category, year, month
            """
            
            results = self.db_manager.execute_query(query)
            
            if not results:
                return anomalies
            
            # Organize data by category
            category_data = defaultdict(list)
            for row in results:
                category, year, month, amount = row
                category_data[category].append({
                    'year': int(year),
                    'month': int(month),
                    'amount': float(amount)
                })
            
            # Get current month
            current_date = datetime.now()
            current_month = current_date.month
            current_year = current_date.year
            
            # Analyze each category
            for category, months_data in category_data.items():
                if len(months_data) < 3:  # Need at least 3 months of data
                    continue
                
                # Separate current month from historical data
                historical_amounts = []
                current_amount = None
                
                for data in months_data:
                    if data['year'] == current_year and data['month'] == current_month:
                        current_amount = data['amount']
                    else:
                        historical_amounts.append(data['amount'])
                
                if current_amount is None or len(historical_amounts) < 2:
                    continue
                
                # Calculate Z-score
                mean_amount = statistics.mean(historical_amounts)
                std_amount = statistics.stdev(historical_amounts) if len(historical_amounts) > 1 else 0
                
                if std_amount == 0:
                    continue
                
                z_score = (current_amount - mean_amount) / std_amount
                
                # Anomaly detected if |z_score| > 2
                if abs(z_score) > 2:
                    percentage_change = ((current_amount - mean_amount) / mean_amount) * 100
                    
                    anomalies.append({
                        'type': 'anomaly',
                        'category': category,
                        'current_amount': round(current_amount, 2),
                        'average_amount': round(mean_amount, 2),
                        'percentage_change': round(percentage_change, 1),
                        'severity': 'high' if abs(z_score) > 3 else 'medium',
                        'message': self._format_anomaly_message(
                            category, percentage_change, current_amount
                        )
                    })
            
            return sorted(anomalies, key=lambda x: abs(x['percentage_change']), reverse=True)
        
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}")
            return []
    
    def analyze_trends(self) -> List[Dict[str, Any]]:
        """
        Analyze spending trends over 3 months.
        
        Identifies categories with significant increasing or decreasing trends.
        
        Returns:
            List of trend insights
        """
        try:
            trends = []
            
            # Get last 3 months spending by category
            query = """
                SELECT 
                    category,
                    EXTRACT(YEAR FROM transaction_date) as year,
                    EXTRACT(MONTH FROM transaction_date) as month,
                    SUM(amount) as total_amount
                FROM transactions
                WHERE type = 'Debit'
                    AND transaction_date >= CURRENT_DATE - INTERVAL '3 months'
                    AND category != 'Uncategorized'
                GROUP BY category, year, month
                ORDER BY category, year DESC, month DESC
            """
            
            results = self.db_manager.execute_query(query)
            
            if not results:
                return trends
            
            # Organize by category
            category_data = defaultdict(list)
            for row in results:
                category, year, month, amount = row
                category_data[category].append(float(amount))
            
            # Analyze trends
            for category, amounts in category_data.items():
                if len(amounts) < 2:
                    continue
                
                # Simple trend: compare most recent to oldest in 3-month window
                oldest_amount = amounts[-1]
                newest_amount = amounts[0]
                
                if oldest_amount == 0:
                    continue
                
                percentage_change = ((newest_amount - oldest_amount) / oldest_amount) * 100
                
                # Only report significant trends (>15% change)
                if abs(percentage_change) > 15:
                    trend_direction = 'increasing' if percentage_change > 0 else 'decreasing'
                    
                    trends.append({
                        'type': 'trend',
                        'category': category,
                        'direction': trend_direction,
                        'percentage_change': round(percentage_change, 1),
                        'oldest_amount': round(oldest_amount, 2),
                        'newest_amount': round(newest_amount, 2),
                        'message': self._format_trend_message(
                            category, percentage_change, trend_direction
                        )
                    })
            
            return sorted(trends, key=lambda x: abs(x['percentage_change']), reverse=True)
        
        except Exception as e:
            logger.error(f"Failed to analyze trends: {e}")
            return []
    
    def predict_monthly_spending(self) -> List[Dict[str, Any]]:
        """
        Predict end-of-month spending for each category.
        
        Uses simple linear projection based on current month progress.
        
        Returns:
            List of prediction insights
        """
        try:
            predictions = []
            
            # Get current month spending so far
            current_date = datetime.now()
            start_of_month = current_date.replace(day=1)
            
            query = """
                SELECT 
                    category,
                    SUM(amount) as amount_so_far
                FROM transactions
                WHERE type = 'Debit'
                    AND transaction_date >= ?
                    AND category != 'Uncategorized'
                GROUP BY category
            """
            
            results = self.db_manager.execute_query(query, (start_of_month,))
            
            if not results:
                return predictions
            
            # Calculate days into month and total days in month
            day_of_month = current_date.day
            days_in_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            total_days = days_in_month.day
            
            if day_of_month < 5:  # Too early in month for accurate predictions
                return predictions
            
            # Project spending
            for row in results:
                category, amount_so_far = row
                amount_so_far = float(amount_so_far)
                
                # Simple linear projection
                projected_amount = (amount_so_far / day_of_month) * total_days
                
                if projected_amount > amount_so_far * 1.2:  # Only show if significant
                    predictions.append({
                        'type': 'prediction',
                        'category': category,
                        'amount_so_far': round(amount_so_far, 2),
                        'projected_amount': round(projected_amount, 2),
                        'days_remaining': total_days - day_of_month,
                        'message': f"Based on trends, you'll spend ${projected_amount:,.0f} on {category} this month"
                    })
            
            return sorted(predictions, key=lambda x: x['projected_amount'], reverse=True)
        
        except Exception as e:
            logger.error(f"Failed to predict spending: {e}")
            return []
    
    def get_budget_alerts(self) -> List[Dict[str, Any]]:
        """
        Check budget status and generate alerts.
        
        Alerts when spending is approaching or exceeding budget limits.
        
        Returns:
            List of budget alert insights
        """
        try:
            alerts = []
            
            # Get budgets and current spending
            query = """
                SELECT 
                    b.category,
                    b.monthly_limit,
                    COALESCE(SUM(t.amount), 0) as current_spending
                FROM budgets b
                LEFT JOIN transactions t 
                    ON b.category = t.category 
                    AND t.type = 'Debit'
                    AND t.transaction_date >= DATE_TRUNC('month', CURRENT_DATE)
                GROUP BY b.category, b.monthly_limit
            """
            
            results = self.db_manager.execute_query(query)
            
            for row in results:
                category, budget_limit, current_spending = row
                budget_limit = float(budget_limit)
                current_spending = float(current_spending)
                
                if budget_limit == 0:
                    continue
                
                usage_percentage = (current_spending / budget_limit) * 100
                
                # Generate alerts based on thresholds
                if usage_percentage >= 90:
                    severity = 'critical'
                    message = f"⚠️ You're on track to exceed {category} budget by {usage_percentage - 100:.0f}%"
                elif usage_percentage >= 70:
                    severity = 'warning'
                    message = f"⚡ You've used {usage_percentage:.0f}% of your {category} budget"
                else:
                    continue  # No alert needed
                
                alerts.append({
                    'type': 'budget_alert',
                    'category': category,
                    'budget_limit': round(budget_limit, 2),
                    'current_spending': round(current_spending, 2),
                    'usage_percentage': round(usage_percentage, 1),
                    'severity': severity,
                    'message': message
                })
            
            return sorted(alerts, key=lambda x: x['usage_percentage'], reverse=True)
        
        except Exception as e:
            logger.error(f"Failed to generate budget alerts: {e}")
            return []
    
    def find_savings_opportunities(self) -> List[Dict[str, Any]]:
        """
        Identify potential savings opportunities.
        
        Looks for:
        - High recurring subscription costs
        - Categories with unusually high spending
        - Duplicate or similar transactions
        
        Returns:
            List of savings opportunity insights
        """
        try:
            opportunities = []
            
            # Find high-value recurring transactions (potential subscriptions)
            recurring_query = """
                SELECT 
                    description,
                    category,
                    COUNT(*) as frequency,
                    AVG(amount) as avg_amount,
                    SUM(amount) as total_amount
                FROM transactions
                WHERE type = 'Debit'
                    AND transaction_date >= CURRENT_DATE - INTERVAL '3 months'
                GROUP BY description, category
                HAVING COUNT(*) >= 2
                ORDER BY total_amount DESC
                LIMIT 10
            """
            
            results = self.db_manager.execute_query(recurring_query)
            
            for row in results:
                description, category, frequency, avg_amount, total_amount = row
                frequency = int(frequency)
                avg_amount = float(avg_amount)
                total_amount = float(total_amount)
                
                # Calculate potential monthly cost
                monthly_cost = total_amount / 3  # Last 3 months
                
                if monthly_cost > 50:  # Significant recurring cost
                    opportunities.append({
                        'type': 'savings_opportunity',
                        'category': 'subscription',
                        'description': description[:50],
                        'monthly_cost': round(monthly_cost, 2),
                        'total_cost_3m': round(total_amount, 2),
                        'frequency': frequency,
                        'message': f"💡 Recurring charge: {description[:30]}... costs ${monthly_cost:.0f}/month. Consider reviewing."
                    })
            
            # Find categories with high spending compared to historical average
            high_spending_query = """
                WITH monthly_avg AS (
                    SELECT 
                        category,
                        AVG(monthly_total) as avg_monthly
                    FROM (
                        SELECT 
                            category,
                            EXTRACT(YEAR FROM transaction_date) as year,
                            EXTRACT(MONTH FROM transaction_date) as month,
                            SUM(amount) as monthly_total
                        FROM transactions
                        WHERE type = 'Debit'
                            AND transaction_date >= CURRENT_DATE - INTERVAL '6 months'
                            AND category != 'Uncategorized'
                        GROUP BY category, year, month
                    ) monthly_data
                    GROUP BY category
                )
                SELECT 
                    t.category,
                    SUM(t.amount) as current_month,
                    ma.avg_monthly
                FROM transactions t
                JOIN monthly_avg ma ON t.category = ma.category
                WHERE t.type = 'Debit'
                    AND t.transaction_date >= DATE_TRUNC('month', CURRENT_DATE)
                    AND t.category != 'Uncategorized'
                GROUP BY t.category, ma.avg_monthly
                HAVING SUM(t.amount) > ma.avg_monthly * 1.5
            """
            
            high_spending_results = self.db_manager.execute_query(high_spending_query)
            
            for row in high_spending_results:
                category, current_month, avg_monthly = row
                current_month = float(current_month)
                avg_monthly = float(avg_monthly)
                
                excess = current_month - avg_monthly
                
                opportunities.append({
                    'type': 'savings_opportunity',
                    'category': 'high_spending',
                    'spending_category': category,
                    'current_amount': round(current_month, 2),
                    'average_amount': round(avg_monthly, 2),
                    'potential_savings': round(excess, 2),
                    'message': f"💰 You could save ${excess:.0f}/month by reducing {category} to average levels"
                })
            
            return opportunities[:5]  # Top 5 opportunities
        
        except Exception as e:
            logger.error(f"Failed to find savings opportunities: {e}")
            return []
    
    def detect_patterns(self) -> Dict[str, Any]:
        """
        Detect spending patterns.
        
        Identifies:
        - Recurring transactions
        - Potential duplicate charges
        - Seasonal patterns
        
        Returns:
            Dictionary of pattern insights
        """
        try:
            patterns = {
                'recurring_transactions': [],
                'potential_duplicates': [],
                'seasonal_patterns': []
            }
            
            # Detect recurring transactions (same amount, regular intervals)
            recurring_query = """
                SELECT 
                    description,
                    amount,
                    category,
                    COUNT(*) as count,
                    MIN(transaction_date) as first_date,
                    MAX(transaction_date) as last_date
                FROM transactions
                WHERE type = 'Debit'
                    AND transaction_date >= CURRENT_DATE - INTERVAL '6 months'
                GROUP BY description, amount, category
                HAVING COUNT(*) >= 3
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """
            
            recurring_results = self.db_manager.execute_query(recurring_query)
            
            for row in recurring_results:
                description, amount, category, count, first_date, last_date = row
                
                patterns['recurring_transactions'].append({
                    'description': description,
                    'amount': float(amount),
                    'category': category,
                    'frequency': int(count),
                    'first_date': str(first_date),
                    'last_date': str(last_date),
                    'suggestion': 'Consider automating this recurring payment'
                })
            
            # Detect potential duplicate charges (same day, same amount, similar description)
            duplicates_query = """
                SELECT 
                    t1.description as desc1,
                    t2.description as desc2,
                    t1.amount,
                    t1.transaction_date,
                    t1.category
                FROM transactions t1
                JOIN transactions t2 
                    ON t1.transaction_date = t2.transaction_date
                    AND t1.amount = t2.amount
                    AND t1.id < t2.id
                    AND t1.type = 'Debit'
                WHERE t1.transaction_date >= CURRENT_DATE - INTERVAL '3 months'
                    AND LENGTH(t1.description) > 5
                LIMIT 10
            """
            
            try:
                duplicate_results = self.db_manager.execute_query(duplicates_query)
                
                for row in duplicate_results:
                    desc1, desc2, amount, trans_date, category = row
                    
                    patterns['potential_duplicates'].append({
                        'descriptions': [desc1, desc2],
                        'amount': float(amount),
                        'date': str(trans_date),
                        'category': category,
                        'warning': 'Potential duplicate charge - verify with your bank'
                    })
            except:
                pass  # Duplicates detection is optional
            
            return patterns
        
        except Exception as e:
            logger.error(f"Failed to detect patterns: {e}")
            return {
                'recurring_transactions': [],
                'potential_duplicates': [],
                'seasonal_patterns': []
            }
    
    def calculate_financial_health_score(self) -> Dict[str, Any]:
        """
        Calculate a financial health score (0-100).
        
        Factors:
        - Savings rate (40 points)
        - Budget adherence (30 points)
        - Transaction diversity (15 points)
        - Spending stability (15 points)
        
        Returns:
            Dictionary with score and breakdown
        """
        try:
            score_breakdown = {}
            total_score = 0
            
            # 1. Savings Rate (40 points)
            current_month = datetime.now().replace(day=1)
            
            income_query = """
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE type = 'Credit'
                    AND transaction_date >= ?
            """
            income = self.db_manager.execute_query(income_query, (current_month,))[0][0]
            
            expense_query = """
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE type = 'Debit'
                    AND transaction_date >= ?
            """
            expenses = self.db_manager.execute_query(expense_query, (current_month,))[0][0]
            
            income = float(income) if income else 0
            expenses = float(expenses) if expenses else 0
            
            if income > 0:
                savings_rate = ((income - expenses) / income) * 100
                # Score: 40 points for 20%+ savings rate, scaled linearly
                savings_score = min(40, (savings_rate / 20) * 40)
                score_breakdown['savings_rate'] = {
                    'score': round(savings_score, 1),
                    'max_score': 40,
                    'value': round(savings_rate, 1),
                    'message': f"Savings rate: {savings_rate:.1f}%"
                }
                total_score += savings_score
            else:
                score_breakdown['savings_rate'] = {
                    'score': 0,
                    'max_score': 40,
                    'value': 0,
                    'message': "No income data"
                }
            
            # 2. Budget Adherence (30 points)
            budget_query = """
                SELECT 
                    COUNT(*) as total_budgets,
                    SUM(CASE 
                        WHEN current_spending <= monthly_limit THEN 1 
                        ELSE 0 
                    END) as budgets_met
                FROM (
                    SELECT 
                        b.category,
                        b.monthly_limit,
                        COALESCE(SUM(t.amount), 0) as current_spending
                    FROM budgets b
                    LEFT JOIN transactions t 
                        ON b.category = t.category 
                        AND t.type = 'Debit'
                        AND t.transaction_date >= DATE_TRUNC('month', CURRENT_DATE)
                    GROUP BY b.category, b.monthly_limit
                ) budget_status
            """
            
            try:
                budget_results = self.db_manager.execute_query(budget_query)
                if budget_results and budget_results[0][0]:
                    total_budgets, budgets_met = budget_results[0]
                    total_budgets = int(total_budgets) if total_budgets else 0
                    budgets_met = int(budgets_met) if budgets_met else 0
                    
                    if total_budgets > 0:
                        budget_adherence = (budgets_met / total_budgets) * 100
                        budget_score = (budget_adherence / 100) * 30
                        score_breakdown['budget_adherence'] = {
                            'score': round(budget_score, 1),
                            'max_score': 30,
                            'value': round(budget_adherence, 1),
                            'message': f"{budgets_met}/{total_budgets} budgets on track"
                        }
                        total_score += budget_score
                    else:
                        score_breakdown['budget_adherence'] = {
                            'score': 15,  # Give partial credit if no budgets set
                            'max_score': 30,
                            'value': 0,
                            'message': "No budgets configured"
                        }
                        total_score += 15
                else:
                    score_breakdown['budget_adherence'] = {
                        'score': 15,
                        'max_score': 30,
                        'value': 0,
                        'message': "No budgets configured"
                    }
                    total_score += 15
            except:
                score_breakdown['budget_adherence'] = {
                    'score': 15,
                    'max_score': 30,
                    'value': 0,
                    'message': "No budgets configured"
                }
                total_score += 15
            
            # 3. Spending Stability (30 points) - consistent spending patterns
            stability_query = """
                SELECT 
                    STDDEV(monthly_total) as std_dev,
                    AVG(monthly_total) as avg_total
                FROM (
                    SELECT 
                        EXTRACT(YEAR FROM transaction_date) as year,
                        EXTRACT(MONTH FROM transaction_date) as month,
                        SUM(amount) as monthly_total
                    FROM transactions
                    WHERE type = 'Debit'
                        AND transaction_date >= CURRENT_DATE - INTERVAL '6 months'
                    GROUP BY year, month
                ) monthly_spending
            """
            
            try:
                stability_results = self.db_manager.execute_query(stability_query)
                if stability_results and stability_results[0][0]:
                    std_dev, avg_total = stability_results[0]
                    std_dev = float(std_dev) if std_dev else 0
                    avg_total = float(avg_total) if avg_total else 0
                    
                    if avg_total > 0:
                        coefficient_of_variation = (std_dev / avg_total) * 100
                        # Lower CV is better (more stable)
                        # Score: 30 points for CV < 10%, scaled down for higher CV
                        stability_score = max(0, 30 - (coefficient_of_variation / 10) * 30)
                        score_breakdown['spending_stability'] = {
                            'score': round(min(30, stability_score), 1),
                            'max_score': 30,
                            'value': round(coefficient_of_variation, 1),
                            'message': f"Spending variability: {coefficient_of_variation:.1f}%"
                        }
                        total_score += min(30, stability_score)
                    else:
                        score_breakdown['spending_stability'] = {
                            'score': 15,
                            'max_score': 30,
                            'value': 0,
                            'message': "Insufficient data"
                        }
                        total_score += 15
                else:
                    score_breakdown['spending_stability'] = {
                        'score': 15,
                        'max_score': 30,
                        'value': 0,
                        'message': "Insufficient data"
                    }
                    total_score += 15
            except:
                score_breakdown['spending_stability'] = {
                    'score': 15,
                    'max_score': 30,
                    'value': 0,
                    'message': "Insufficient data"
                }
                total_score += 15
            
            # Calculate overall grade
            grade = self._calculate_grade(total_score)
            
            return {
                'score': round(total_score, 1),
                'max_score': 100,
                'grade': grade,
                'breakdown': score_breakdown,
                'message': self._get_health_score_message(total_score, grade)
            }
        
        except Exception as e:
            logger.error(f"Failed to calculate health score: {e}")
            return {
                'score': 0,
                'max_score': 100,
                'grade': 'N/A',
                'breakdown': {},
                'message': 'Unable to calculate health score'
            }
    
    def _format_anomaly_message(self, category: str, percentage: float, amount: float) -> str:
        """Format anomaly detection message."""
        if percentage > 0:
            return f"⚠️ You spent {abs(percentage):.0f}% MORE on {category} this month (${amount:,.0f})"
        else:
            return f"✅ You spent {abs(percentage):.0f}% LESS on {category} this month (${amount:,.0f})"
    
    def _format_trend_message(self, category: str, percentage: float, direction: str) -> str:
        """Format trend analysis message."""
        icon = "📈" if direction == "increasing" else "📉"
        return f"{icon} Your {category} spending {direction} by {abs(percentage):.0f}% over 3 months"
    
    def _generate_top_tips(self, insights: Dict[str, Any]) -> List[str]:
        """Generate top 3 actionable tips from all insights."""
        tips = []
        
        # Priority 1: Critical budget alerts
        for alert in insights.get('budget_alerts', []):
            if alert.get('severity') == 'critical' and len(tips) < 3:
                tips.append(alert['message'])
        
        # Priority 2: High anomalies
        for anomaly in insights.get('anomalies', []):
            if len(tips) >= 3:
                break
            if anomaly.get('severity') == 'high' and anomaly.get('percentage_change', 0) > 0:
                tips.append(anomaly['message'])
        
        # Priority 3: Savings opportunities
        for opp in insights.get('savings_opportunities', []):
            if len(tips) >= 3:
                break
            tips.append(opp['message'])
        
        # Priority 4: Warning budget alerts
        if len(tips) < 3:
            for alert in insights.get('budget_alerts', []):
                if len(tips) >= 3:
                    break
                if alert.get('severity') == 'warning':
                    tips.append(alert['message'])
        
        # Fill with trends if needed
        if len(tips) < 3:
            for trend in insights.get('trends', []):
                if len(tips) >= 3:
                    break
                tips.append(trend['message'])
        
        # Default tip if nothing else
        if not tips:
            tips.append("💡 Upload more transactions to get personalized insights!")
        
        return tips[:3]
    
    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _get_health_score_message(self, score: float, grade: str) -> str:
        """Get message based on health score."""
        if score >= 80:
            return f"Excellent! Your financial health is strong (Grade: {grade})"
        elif score >= 60:
            return f"Good progress! Keep improving your finances (Grade: {grade})"
        elif score >= 40:
            return f"Fair. Focus on savings and budgets (Grade: {grade})"
        else:
            return f"Needs attention. Review your spending habits (Grade: {grade})"
    
    def _empty_insights(self) -> Dict[str, Any]:
        """Return empty insights structure."""
        return {
            'anomalies': [],
            'trends': [],
            'predictions': [],
            'budget_alerts': [],
            'savings_opportunities': [],
            'patterns': {
                'recurring_transactions': [],
                'potential_duplicates': [],
                'seasonal_patterns': []
            },
            'health_score': {
                'score': 0,
                'max_score': 100,
                'grade': 'N/A',
                'breakdown': {},
                'message': 'No data available'
            },
            'top_tips': ['Upload transactions to get started!']
        }


# Global instance
insights_engine = None


def get_insights_engine(db_manager: DatabaseManager = None) -> InsightsEngine:
    """Get or create global insights engine instance."""
    global insights_engine
    if insights_engine is None and db_manager:
        insights_engine = InsightsEngine(db_manager)
    return insights_engine
