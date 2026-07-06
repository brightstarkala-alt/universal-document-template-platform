from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.schemas.company import CurrentCompany
from app.schemas.file import SignedUrlResponse
from app.schemas.preview import TemplatePreviewResponse
from app.schemas.template import (
    TemplateArtifact,
    TemplateManifest,
    TemplateManifestMetadata,
)

FAKE_COMPANY = CurrentCompany(id="company-1", name="Acme Inc", slug="acme", role="owner")

FAKE_PREVIEW = TemplatePreviewResponse(
    artifact=TemplateArtifact(
        schema_version="1.0",
        generator_version="1.0",
        source_ai_extraction_id="extraction-1",
        source_parsed_document_id="parsed-1",
        version=1,
        generated_at=datetime.now(UTC),
        html='<section class="page">hello</section>',
        css="body { margin: 0; }",
        manifest=TemplateManifest(
            pages=[],
            fields=[],
            repeating_sections=[],
            assets=[],
            metadata=TemplateManifestMetadata(
                source_format="pdf",
                page_count=1,
                sheet_count=0,
                field_count=0,
                section_count=0,
                asset_count=0,
                unmapped_field_count=0,
                unmapped_section_count=0,
                duration_ms=1.0,
            ),
        ),
    ),
    asset_urls={},
)


def _mock_authenticated_user() -> MagicMock:
    fake_user = MagicMock(id="user-1", email="test@example.com")
    return MagicMock(user=fake_user)


def test_read_latest_preview_requires_authentication(client):
    response = client.get("/api/v1/files/file-1/preview")
    assert response.status_code == 401


def test_read_latest_preview_returns_artifact_and_asset_urls(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.preview.preview_service.get_latest_preview", return_value=FAKE_PREVIEW
        ) as mock_get_latest,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/preview", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["artifact"]["version"] == 1
    assert body["asset_urls"] == {}
    mock_get_latest.assert_called_once_with(company_id="company-1", file_id="file-1")


def test_read_preview_version_returns_artifact(client):
    fake_auth_response = _mock_authenticated_user()

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.preview.preview_service.get_preview_by_version", return_value=FAKE_PREVIEW
        ) as mock_get_version,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/preview/1", headers={"Authorization": "Bearer good-token"}
        )

    assert response.status_code == 200
    mock_get_version.assert_called_once_with(company_id="company-1", file_id="file-1", version=1)


def test_refresh_preview_asset_url_requires_authentication(client):
    response = client.get("/api/v1/files/file-1/preview/assets/asset-1/signed-url")
    assert response.status_code == 401


def test_refresh_preview_asset_url_returns_signed_url(client):
    fake_auth_response = _mock_authenticated_user()
    fake_signed_url = SignedUrlResponse(url="https://signed.example/asset-1.png", expires_in=300)

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.preview.preview_service.refresh_asset_url", return_value=fake_signed_url
        ) as mock_refresh,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/preview/assets/asset-1/signed-url",
            headers={"Authorization": "Bearer good-token"},
        )

    assert response.status_code == 200
    assert response.json()["url"] == "https://signed.example/asset-1.png"
    mock_refresh.assert_called_once_with(
        company_id="company-1", file_id="file-1", asset_id="asset-1", version=None
    )


def test_refresh_preview_asset_url_passes_version_query_param(client):
    fake_auth_response = _mock_authenticated_user()
    fake_signed_url = SignedUrlResponse(url="https://signed.example/asset-1.png", expires_in=300)

    with (
        patch("app.api.deps.get_supabase_admin") as mock_get_admin,
        patch("app.api.deps.company_service.get_company_for_user", return_value=FAKE_COMPANY),
        patch(
            "app.api.v1.preview.preview_service.refresh_asset_url", return_value=fake_signed_url
        ) as mock_refresh,
    ):
        mock_get_admin.return_value.auth.get_user.return_value = fake_auth_response
        response = client.get(
            "/api/v1/files/file-1/preview/assets/asset-1/signed-url?version=2",
            headers={"Authorization": "Bearer good-token"},
        )

    assert response.status_code == 200
    mock_refresh.assert_called_once_with(
        company_id="company-1", file_id="file-1", asset_id="asset-1", version=2
    )
