"""HTTP surface of people memory: strangers are refused, and there is no open person-lookup route."""
import base64
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app, settings         # noqa: E402

client = TestClient(app)
AUTH = {"Authorization": f"Bearer {settings.api_token}"} if settings.api_token else {}


def test_recall_refuses_someone_not_saved():
    r = client.get(f"/people/stranger-{uuid.uuid4().hex}", headers=AUTH)
    assert r.status_code == 404


def test_unknown_face_is_not_identified():
    image = base64.b64encode(os.urandom(256)).decode()
    r = client.post("/face/recognize", json={"image_b64": image}, headers=AUTH)
    assert r.status_code == 200 and r.json()["recognized"] is False


def test_no_open_lookup_routes():
    paths = {route.path for route in app.routes}
    assert {"/face/enroll", "/face/recognize", "/people/{name}"} <= paths
    assert not any("osint" in p for p in paths)
