from unittest.mock import MagicMock, patch

from app.schemas.company import CurrentCompany
from app.schemas.file import SignedUrlResponse
from app.schemas.pdf_metadata import PDFMetadata

FAKE_COMPANY = CurrentCompany(id="company-1", name="Acme Inc", slug="acme", role="owner")

FAKE_PDF = PDFMetadata(
    id="pdf-1",
    company_id="company-1",
    file_id="file-1",
    source_template_id="template-1",
    version=1,
    schema_version="1.0",
    generator_version="1.0",
    status="completed",
    storage_path="company-1/file-1/pdfs/1.0-v1-x.pdf",
    page_count=1,
    size_bytes=2048,
    duration_ms=42.0,
    error_message=None,
    created_at="2026-01-01T00:00:00Z",
)


def _mock_authenticated_user() -> MagicMock:
    fake_user = MagicMock(id="user-1", email="test@example.com")
    return MagicMock(user=fake_user)


def test_generate_pdf_requires_authentication(client):
    response = client.post("/api/v1/files/file-1/pdf")
    assert response.status_code == 401


def test_generate_pdf_returns_pdf_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.pdf.pdf_generation_service.generate_pdf", return_value=FAKE_PDF
        ) as mock_generate,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.post(
            "/api/v1/files/file-1/pdf", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "pdf-1"
    assert body["version"] == 1
    mock_generate.assert_called_once_with(company_id="company-1", file_id="file-1", force=False)


def test_generate_pdf_passes_force_query_param(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.pdf.pdf_generation_service.generate_pdf", return_value=FAKE_PDF
        ) as mock_generate,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.post(
            "/api/v1/files/file-1/pdf?force=true", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    mock_generate.assert_called_once_with(company_id="company-1", file_id="file-1", force=True)


def test_read_latest_pdf_requires_authentication(client):
    response = client.get("/api/v1/files/file-1/pdf")
    assert response.status_code == 401


def test_read_latest_pdf_returns_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.pdf.pdf_generation_service.get_latest_pdf", return_value=FAKE_PDF
        ),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/pdf", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    assert response.json()["id"] == "pdf-1"


def test_read_pdf_versions_returns_list(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.pdf.pdf_generation_service.list_pdfs", return_value=[FAKE_PDF]
        ),
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/pdf/versions", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["id"] == "pdf-1"


def test_read_pdf_signed_url_returns_signed_url(client):
    fake_auth_response = _mock_authenticated_user()
    fake_signed_url = SignedUrlResponse(url="https://signed.example/x.pdf", expires_in=300)

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.pdf.pdf_generation_service.get_download_url",
            return_value=fake_signed_url,
        ) as mock_get_url,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/pdf/signed-url", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    assert response.json()["url"] == "https://signed.example/x.pdf"
    mock_get_url.assert_called_once_with(company_id="company-1", file_id="file-1", version=None)


def test_read_pdf_signed_url_passes_version_query_param(client):
    fake_auth_response = _mock_authenticated_user()
    fake_signed_url = SignedUrlResponse(url="https://signed.example/v2.pdf", expires_in=300)

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.pdf.pdf_generation_service.get_download_url",
            return_value=fake_signed_url,
        ) as mock_get_url,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/pdf/signed-url?version=2",
            headers={"Authorization": "Bearer good-token"},
        )

    assert response.status_code == 200
    mock_get_url.assert_called_once_with(company_id="company-1", file_id="file-1", version=2)


def test_read_pdf_version_returns_metadata(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.pdf.pdf_generation_service.get_pdf_by_version", return_value=FAKE_PDF
        ) as mock_get_version,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/pdf/1", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    assert response.json()["version"] == 1
    mock_get_version.assert_called_once_with(company_id="company-1", file_id="file-1", version=1)
