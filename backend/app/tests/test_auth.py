from unittest.mock import MagicMock, patch


def test_me_without_token_returns_401(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_me_with_invalid_token_returns_401(client):
    with patch("app.api.deps.get_supabase_admin") as mock_get_admin:
        mock_get_admin.return_value.auth.get_user.side_effect = Exception("invalid token")
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_with_no_user_on_response_returns_401(client):
    with patch("app.api.deps.get_supabase_admin") as mock_get_admin:
        mock_get_admin.return_value.auth.get_user.return_value = MagicMock(user=None)
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer some-token"})

    assert response.status_code == 401


def test_me_with_valid_token_returns_current_user(client):
    fake_user = MagicMock(id="user-123", email="test@example.com")
    fake_response = MagicMock(user=fake_user)

    with patch("app.api.deps.get_supabase_admin") as mock_get_admin:
        mock_get_admin.return_value.auth.get_user.return_value = fake_response
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer good-token"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "user-123"
    assert body["email"] == "test@example.com"
