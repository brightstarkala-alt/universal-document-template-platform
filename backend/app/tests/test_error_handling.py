def test_404_on_unknown_route_returns_standard_envelope(client):
    response = client.get("/api/v1/this-route-does-not-exist")
    assert response.status_code == 404

    body = response.json()
    assert body["success"] is False
    assert "code" in body["error"]
    assert "message" in body["error"]
