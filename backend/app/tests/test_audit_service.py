from unittest.mock import MagicMock, patch

from app.services import audit_service


def test_record_event_inserts_expected_row() -> None:
    mock_client = MagicMock()

    with patch("app.services.audit_service.get_supabase_admin", return_value=mock_client):
        audit_service.record_event(
            company_id="company-1",
            user_id="user-1",
            action="company.viewed",
            entity_type="company",
            entity_id="company-1",
            metadata={"source": "test"},
        )

    mock_client.table.assert_called_once_with("audit_logs")
    mock_client.table.return_value.insert.assert_called_once_with(
        {
            "company_id": "company-1",
            "user_id": "user-1",
            "action": "company.viewed",
            "entity_type": "company",
            "entity_id": "company-1",
            "metadata": {"source": "test"},
        }
    )
    mock_client.table.return_value.insert.return_value.execute.assert_called_once()
