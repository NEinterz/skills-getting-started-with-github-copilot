"""
Comprehensive tests for Mergington High School Management System API

Tests all FastAPI endpoints with fixtures to reset in-memory data between tests.
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities
import copy


@pytest.fixture
def client():
    """Provide a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """
    Fixture to reset the in-memory activities data before each test.
    This ensures tests don't interfere with each other.
    """
    # Store the original state of activities
    original_activities = copy.deepcopy(activities)

    yield

    # Reset activities to original state after test
    activities.clear()
    activities.update(original_activities)


# ==================== Root Endpoint Tests ====================

def test_root_redirect(client, reset_activities):
    """Test that root endpoint redirects to static index.html"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


# ==================== Get Activities Endpoint Tests ====================

def test_get_activities_success(client, reset_activities):
    """Test getting all activities returns the complete activities dictionary"""
    response = client.get("/activities")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)
    assert len(data) > 0

    # Check that all expected activities are present
    expected_activities = [
        "Chess Club", "Programming Class", "Gym Class",
        "Soccer", "Swimming", "Drawing", "Singing", "Reading", "Math"
    ]
    for activity in expected_activities:
        assert activity in data
        assert "description" in data[activity]
        assert "participants" in data[activity]


def test_get_activities_has_correct_structure(client, reset_activities):
    """Test that activities have the expected structure"""
    response = client.get("/activities")
    data = response.json()

    # Test a fully defined activity
    chess = data["Chess Club"]
    assert chess["description"] == "Learn strategies and compete in chess tournaments"
    assert chess["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
    assert chess["max_participants"] == 12
    assert len(chess["participants"]) == 2
    assert "michael@mergington.edu" in chess["participants"]

    # Test a minimally defined activity
    soccer = data["Soccer"]
    assert "description" in soccer
    assert "participants" in soccer
    assert soccer["participants"] == []


# ==================== Signup Endpoint Tests ====================

def test_signup_success(client, reset_activities):
    """Test successful signup for an activity"""
    response = client.post("/activities/Soccer/signup?email=test@mergington.edu")
    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert "test@mergington.edu" in data["message"]
    assert "Soccer" in data["message"]

    # Verify the participant was added
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert "test@mergington.edu" in activities_data["Soccer"]["participants"]


def test_signup_activity_not_found(client, reset_activities):
    """Test signup for non-existent activity returns 404"""
    response = client.post("/activities/NonExistent/signup?email=test@mergington.edu")
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "Activity not found" in data["detail"]


def test_signup_already_signed_up(client, reset_activities):
    """Test signup when student is already signed up returns 400"""
    # First signup
    client.post("/activities/Soccer/signup?email=test@mergington.edu")

    # Try to signup again
    response = client.post("/activities/Soccer/signup?email=test@mergington.edu")
    assert response.status_code == 400

    data = response.json()
    assert "detail" in data
    assert "already signed up" in data["detail"]


def test_signup_multiple_students(client, reset_activities):
    """Test multiple students can sign up for the same activity"""
    emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]

    for email in emails:
        response = client.post(f"/activities/Soccer/signup?email={email}")
        assert response.status_code == 200

    # Verify all were added
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    soccer_participants = activities_data["Soccer"]["participants"]
    for email in emails:
        assert email in soccer_participants
    assert len(soccer_participants) == 3


# ==================== Unregister Endpoint Tests ====================

def test_unregister_success(client, reset_activities):
    """Test successful unregister from an activity"""
    # First sign up
    client.post("/activities/Soccer/signup?email=test@mergington.edu")

    # Then unregister
    response = client.post("/activities/Soccer/unregister?email=test@mergington.edu")
    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert "test@mergington.edu" in data["message"]
    assert "Soccer" in data["message"]

    # Verify the participant was removed
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert "test@mergington.edu" not in activities_data["Soccer"]["participants"]


def test_unregister_activity_not_found(client, reset_activities):
    """Test unregister from non-existent activity returns 404"""
    response = client.post("/activities/NonExistent/unregister?email=test@mergington.edu")
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "Activity not found" in data["detail"]


def test_unregister_not_signed_up(client, reset_activities):
    """Test unregister when student is not signed up returns 400"""
    response = client.post("/activities/Soccer/unregister?email=test@mergington.edu")
    assert response.status_code == 400

    data = response.json()
    assert "detail" in data
    assert "not signed up" in data["detail"]


def test_unregister_from_activity_with_existing_participants(client, reset_activities):
    """Test unregistering from an activity that already has participants"""
    # Use Chess Club which has existing participants
    response = client.post("/activities/Chess%20Club/unregister?email=michael@mergington.edu")
    assert response.status_code == 200

    # Verify the participant was removed
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    chess_participants = activities_data["Chess Club"]["participants"]
    assert "michael@mergington.edu" not in chess_participants
    assert "daniel@mergington.edu" in chess_participants  # Other participant should remain


# ==================== Integration Tests ====================

def test_signup_then_unregister_workflow(client, reset_activities):
    """Test complete workflow: signup then unregister"""
    email = "workflow@mergington.edu"
    activity = "Drawing"

    # Sign up
    signup_response = client.post(f"/activities/{activity}/signup?email={email}")
    assert signup_response.status_code == 200

    # Verify signed up
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert email in activities_data[activity]["participants"]

    # Unregister
    unregister_response = client.post(f"/activities/{activity}/unregister?email={email}")
    assert unregister_response.status_code == 200

    # Verify unregistered
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert email not in activities_data[activity]["participants"]


def test_activities_data_integrity(client, reset_activities):
    """Test that activities data maintains integrity across operations"""
    # Get initial state
    initial_response = client.get("/activities")
    initial_data = initial_response.json()

    # Perform some operations
    client.post("/activities/Soccer/signup?email=integrity1@mergington.edu")
    client.post("/activities/Soccer/signup?email=integrity2@mergington.edu")
    client.post("/activities/Soccer/unregister?email=integrity1@mergington.edu")

    # Get final state
    final_response = client.get("/activities")
    final_data = final_response.json()

    # Check that other activities weren't affected
    for activity_name in initial_data:
        if activity_name != "Soccer":
            assert initial_data[activity_name] == final_data[activity_name]

    # Check Soccer has correct final state
    soccer = final_data["Soccer"]
    assert "integrity1@mergington.edu" not in soccer["participants"]
    assert "integrity2@mergington.edu" in soccer["participants"]