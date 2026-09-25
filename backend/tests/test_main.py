from main import health


def test_health_returns_ok_status():
    assert health() == {"status": "ok"}