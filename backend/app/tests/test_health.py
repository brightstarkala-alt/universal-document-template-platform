def test_health_check_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert "environment" in body
    assert "version" in body
    assert "timestamp" in body


def test_health_check_has_request_id_header(client):
    response = client.get("/api/v1/health")
    assert "x-request-id" in {k.lower() for k in response.headers}
