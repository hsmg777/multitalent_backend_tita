def test_health_endpoint():
    from app import create_app
    client = create_app("dev").test_client()
    r = client.get("/api/v1/health/")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"
