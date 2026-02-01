"""
Tests for goals management functionality.
"""

import pytest
from datetime import date, datetime, timedelta
from src.goals import (
    create_goal, add_contribution, get_all_goals, get_goal_by_id,
    calculate_goal_metrics, get_milestone, update_goal, delete_goal,
    get_goal_contributions, get_top_goals, GOAL_TYPES
)
from src.database import DatabaseManager


class TestGoals:
    """Test suite for financial goals functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Setup: Create a fresh database connection
        db = DatabaseManager()
        
        # Clean up any existing test data
        with db.get_connection() as conn:
            conn.execute("DELETE FROM goal_contributions")
            conn.execute("DELETE FROM goals")
        
        yield
        
        # Teardown: Clean up test data
        with db.get_connection() as conn:
            conn.execute("DELETE FROM goal_contributions")
            conn.execute("DELETE FROM goals")
    
    def test_create_goal(self):
        """Test creating a new financial goal."""
        goal_id = create_goal(
            name="Emergency Fund",
            goal_type="Emergency Fund",
            target_amount=50000.0,
            target_date=date.today() + timedelta(days=365),
            priority=1
        )
        
        assert goal_id is not None, "Goal ID should be returned"
        assert isinstance(goal_id, int), "Goal ID should be an integer"
    
    def test_get_goal_by_id(self):
        """Test retrieving a goal by ID."""
        # Create a goal
        goal_id = create_goal(
            name="Vacation Fund",
            goal_type="Vacation/Travel",
            target_amount=100000.0,
            target_date=date.today() + timedelta(days=180),
            priority=3
        )
        
        # Retrieve the goal
        goal = get_goal_by_id(goal_id)
        
        assert goal is not None, "Goal should be found"
        assert goal['name'] == "Vacation Fund", "Name should match"
        assert goal['goal_type'] == "Vacation/Travel", "Type should match"
        assert goal['target_amount'] == 100000.0, "Target amount should match"
        assert goal['priority'] == 3, "Priority should match"
    
    def test_add_contribution(self):
        """Test adding a contribution to a goal."""
        # Create a goal
        goal_id = create_goal(
            name="Car Fund",
            goal_type="New Car/Bike",
            target_amount=500000.0,
            target_date=date.today() + timedelta(days=730),
            priority=2
        )
        
        # Add a contribution
        success = add_contribution(
            goal_id=goal_id,
            amount=10000.0,
            contribution_date=date.today(),
            notes="Initial deposit"
        )
        
        assert success is True, "Contribution should be added successfully"
        
        # Verify the contribution was added
        goal = get_goal_by_id(goal_id)
        assert goal['current_amount'] == 10000.0, "Current amount should be updated"
    
    def test_multiple_contributions(self):
        """Test adding multiple contributions to a goal."""
        # Create a goal
        goal_id = create_goal(
            name="Education Fund",
            goal_type="Education",
            target_amount=200000.0,
            target_date=date.today() + timedelta(days=1095),
            priority=1
        )
        
        # Add multiple contributions
        add_contribution(goal_id, 20000.0, date.today(), "First deposit")
        add_contribution(goal_id, 15000.0, date.today() - timedelta(days=30), "Second deposit")
        add_contribution(goal_id, 10000.0, date.today() - timedelta(days=60), "Third deposit")
        
        # Verify total
        goal = get_goal_by_id(goal_id)
        assert goal['current_amount'] == 45000.0, "Total contributions should sum correctly"
    
    def test_calculate_goal_metrics(self):
        """Test calculation of goal progress metrics."""
        # Create test goal data
        goal = {
            'target_amount': 100000.0,
            'current_amount': 25000.0,
            'target_date': date.today() + timedelta(days=365),
            'created_at': datetime.now() - timedelta(days=90)
        }
        
        metrics = calculate_goal_metrics(goal)
        
        assert 'progress_percent' in metrics, "Should include progress percentage"
        assert 'remaining_amount' in metrics, "Should include remaining amount"
        assert 'days_remaining' in metrics, "Should include days remaining"
        assert 'months_remaining' in metrics, "Should include months remaining"
        assert 'required_monthly' in metrics, "Should include required monthly savings"
        assert 'milestone' in metrics, "Should include milestone"
        assert 'is_on_track' in metrics, "Should include on-track status"
        
        assert metrics['progress_percent'] == 25.0, "Progress should be 25%"
        assert metrics['remaining_amount'] == 75000.0, "Remaining should be 75000"
    
    def test_milestone_detection(self):
        """Test milestone detection for different progress levels."""
        assert get_milestone(0) == "🚀 Getting Started"
        assert get_milestone(24.9) == "🚀 Getting Started"
        assert get_milestone(25.0) == "🎯 25% Milestone"
        assert get_milestone(49.9) == "🎯 25% Milestone"
        assert get_milestone(50.0) == "🎯 50% Milestone"
        assert get_milestone(74.9) == "🎯 50% Milestone"
        assert get_milestone(75.0) == "🎯 75% Milestone"
        assert get_milestone(99.9) == "🎯 75% Milestone"
        assert get_milestone(100.0) == "🎉 Completed"
        assert get_milestone(105.0) == "🎉 Completed"
    
    def test_update_goal(self):
        """Test updating goal details."""
        # Create a goal
        goal_id = create_goal(
            name="Original Name",
            goal_type="Custom",
            target_amount=50000.0,
            target_date=date.today() + timedelta(days=365),
            priority=5
        )
        
        # Update the goal
        new_target_date = date.today() + timedelta(days=730)
        success = update_goal(
            goal_id=goal_id,
            name="Updated Name",
            target_amount=75000.0,
            target_date=new_target_date,
            priority=2
        )
        
        assert success is True, "Update should succeed"
        
        # Verify updates
        goal = get_goal_by_id(goal_id)
        assert goal['name'] == "Updated Name", "Name should be updated"
        assert goal['target_amount'] == 75000.0, "Target amount should be updated"
        assert goal['priority'] == 2, "Priority should be updated"
    
    def test_delete_goal(self):
        """Test deleting a goal."""
        # Create a goal with contributions
        goal_id = create_goal(
            name="Test Goal",
            goal_type="Custom",
            target_amount=50000.0,
            target_date=date.today() + timedelta(days=365),
            priority=5
        )
        
        add_contribution(goal_id, 5000.0, date.today(), "Test contribution")
        
        # Delete the goal
        success = delete_goal(goal_id)
        assert success is True, "Delete should succeed"
        
        # Verify goal is deleted
        goal = get_goal_by_id(goal_id)
        assert goal is None, "Goal should not exist after deletion"
        
        # Verify contributions are also deleted
        contributions = get_goal_contributions(goal_id)
        assert len(contributions) == 0, "Contributions should be deleted"
    
    def test_get_all_goals(self):
        """Test retrieving all goals."""
        # Create multiple goals
        create_goal("Goal 1", "Emergency Fund", 50000.0, date.today() + timedelta(days=365), 1)
        create_goal("Goal 2", "Vacation/Travel", 100000.0, date.today() + timedelta(days=180), 2)
        create_goal("Goal 3", "New Car/Bike", 500000.0, date.today() + timedelta(days=730), 3)
        
        # Retrieve all goals
        goals = get_all_goals()
        
        assert len(goals) == 3, "Should return all 3 goals"
        assert all('progress_percent' in g for g in goals), "All goals should have metrics"
        
        # Check priority ordering
        assert goals[0]['priority'] <= goals[1]['priority'], "Goals should be ordered by priority"
    
    def test_get_top_goals(self):
        """Test retrieving top priority goals."""
        # Create multiple goals
        create_goal("Priority 1", "Emergency Fund", 50000.0, date.today() + timedelta(days=365), 1)
        create_goal("Priority 2", "Vacation/Travel", 100000.0, date.today() + timedelta(days=180), 2)
        create_goal("Priority 3", "New Car/Bike", 500000.0, date.today() + timedelta(days=730), 3)
        create_goal("Priority 4", "Education", 200000.0, date.today() + timedelta(days=1095), 4)
        create_goal("Priority 5", "Retirement", 1000000.0, date.today() + timedelta(days=3650), 5)
        
        # Get top 3 goals
        top_goals = get_top_goals(limit=3)
        
        assert len(top_goals) == 3, "Should return only 3 goals"
        assert top_goals[0]['priority'] == 1, "First should be highest priority"
        assert top_goals[2]['priority'] == 3, "Last should be third priority"
    
    def test_goal_types_defined(self):
        """Test that all expected goal types are defined."""
        expected_types = [
            "Emergency Fund",
            "Vacation/Travel",
            "New Car/Bike",
            "Home Down Payment",
            "Education",
            "Retirement",
            "Custom"
        ]
        
        assert GOAL_TYPES == expected_types, "All goal types should be defined"
    
    def test_get_goal_contributions(self):
        """Test retrieving contributions for a goal."""
        # Create a goal
        goal_id = create_goal(
            name="Test Goal",
            goal_type="Custom",
            target_amount=100000.0,
            target_date=date.today() + timedelta(days=365),
            priority=5
        )
        
        # Add contributions
        add_contribution(goal_id, 10000.0, date.today(), "First")
        add_contribution(goal_id, 5000.0, date.today() - timedelta(days=30), "Second")
        add_contribution(goal_id, 7500.0, date.today() - timedelta(days=60), "Third")
        
        # Retrieve contributions
        contributions = get_goal_contributions(goal_id)
        
        assert len(contributions) == 3, "Should return all 3 contributions"
        # Should be ordered by date descending
        assert contributions[0]['notes'] == "First", "Most recent should be first"
    
    def test_progress_percent_caps_at_100(self):
        """Test that progress percentage doesn't exceed 100%."""
        goal = {
            'target_amount': 50000.0,
            'current_amount': 75000.0,  # Over the target
            'target_date': date.today() + timedelta(days=365),
            'created_at': datetime.now() - timedelta(days=90)
        }
        
        metrics = calculate_goal_metrics(goal)
        
        assert metrics['progress_percent'] == 100.0, "Progress should be capped at 100%"
        assert metrics['remaining_amount'] == 0.0, "Remaining should be 0 when over target"
    
    def test_required_monthly_zero_when_target_reached(self):
        """Test that required monthly savings is 0 when target is reached."""
        goal = {
            'target_amount': 50000.0,
            'current_amount': 50000.0,  # Target reached
            'target_date': date.today() + timedelta(days=365),
            'created_at': datetime.now() - timedelta(days=90)
        }
        
        metrics = calculate_goal_metrics(goal)
        
        assert metrics['required_monthly'] == 0.0, "Required monthly should be 0 when target reached"
