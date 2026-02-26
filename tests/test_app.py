"""Tests for the Mergington High School API."""

import copy
import pytest
from starlette.testclient import TestClient
from src.app import app, activities


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset the in-memory activities database before each test."""
    original = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(original)


client = TestClient(app)


# ──────────────────────────────────────────────
# GET / (root redirect)
# ──────────────────────────────────────────────


class TestRootRedirect:
    def test_redirects_to_static_index(self):
        # Arrange — no setup needed

        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


# ──────────────────────────────────────────────
# GET /activities
# ──────────────────────────────────────────────


class TestGetActivities:
    def test_returns_all_activities(self):
        # Arrange — no setup needed

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 9

    def test_activity_has_required_fields(self):
        # Arrange
        required_keys = {"description", "schedule", "max_participants", "participants"}

        # Act
        response = client.get("/activities")

        # Assert
        data = response.json()
        for name, details in data.items():
            assert required_keys.issubset(details.keys()), f"{name} missing keys"

    def test_cache_control_headers(self):
        # Arrange — no setup needed

        # Act
        response = client.get("/activities")

        # Assert
        cache_control = response.headers.get("cache-control", "")
        assert "no-store" in cache_control
        assert "no-cache" in cache_control


# ──────────────────────────────────────────────
# POST /activities/{activity_name}/signup
# ──────────────────────────────────────────────


class TestSignup:
    def test_successful_signup(self):
        # Arrange
        activity_name = "Chess Club"
        email = "testuser@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 200
        assert email in response.json()["message"]

    def test_participant_added_to_list(self):
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"

        # Act
        client.post(f"/activities/{activity_name}/signup", params={"email": email})
        response = client.get("/activities")

        # Assert
        participants = response.json()[activity_name]["participants"]
        assert email in participants

    def test_signup_nonexistent_activity_returns_404(self):
        # Arrange
        activity_name = "Nonexistent Club"
        email = "testuser@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_duplicate_signup_returns_400(self):
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # already in participants

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"].lower()


# ──────────────────────────────────────────────
# DELETE /activities/{activity_name}/unregister
# ──────────────────────────────────────────────


class TestUnregister:
    def test_successful_unregister(self):
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # existing participant

        # Act
        response = client.request(
            "DELETE",
            f"/activities/{activity_name}/unregister",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 200
        assert email in response.json()["message"]

    def test_participant_removed_from_list(self):
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"

        # Act
        client.request(
            "DELETE",
            f"/activities/{activity_name}/unregister",
            params={"email": email},
        )
        response = client.get("/activities")

        # Assert
        participants = response.json()[activity_name]["participants"]
        assert email not in participants

    def test_unregister_nonexistent_activity_returns_404(self):
        # Arrange
        activity_name = "Nonexistent Club"
        email = "testuser@mergington.edu"

        # Act
        response = client.request(
            "DELETE",
            f"/activities/{activity_name}/unregister",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_not_signed_up_returns_400(self):
        # Arrange
        activity_name = "Chess Club"
        email = "unknown@mergington.edu"  # not a participant

        # Act
        response = client.request(
            "DELETE",
            f"/activities/{activity_name}/unregister",
            params={"email": email},
        )

        # Assert
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()
