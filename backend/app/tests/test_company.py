from unittest.mock import MagicMock, patch

from app.schemas.company import CurrentCompany


def test_me_without_token_returns_401(client):
    response = client.get("/api/v1/companies/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_without_company_membership_returns_403(client):
    fake_user = MagicMock(id="user-123", email="test@example.com")
    fake_auth_response = MagicMock(user=fake_user)

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=None),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/companies/me", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NO_COMPANY_MEMBERSHIP"


def test_me_with_company_membership_returns_current_company(client):
    fake_user = MagicMock(id="user-123", email="test@example.com")
    fake_auth_response = MagicMock(user=fake_user)
    fake_company = CurrentCompany(id="company-1", name="Acme Inc", slug="acme", role="owner")

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch(
            "app.api.deps.company_service.get_company_for_user",
            return_value=fake_company,
        ),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/companies/me", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body == {"id": "company-1", "name": "Acme Inc", "slug": "acme", "role": "owner"}
