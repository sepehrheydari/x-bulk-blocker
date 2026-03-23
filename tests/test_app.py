import json
import uuid
from unittest.mock import patch

import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.test_client() as c:
        yield c


class TestIndex:
    def test_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200

    def test_returns_html(self, client):
        res = client.get("/")
        assert b"List Bulk Blocker" in res.data

    def test_content_type_html(self, client):
        res = client.get("/")
        assert "text/html" in res.content_type


class TestStart:
    def test_missing_all_fields(self, client):
        res = client.post("/start", data={})
        assert res.status_code == 400

    def test_missing_auth_token(self, client):
        res = client.post("/start", data={"list_url": "https://x.com/i/lists/123", "ct0": "x"})
        assert res.status_code == 400

    def test_missing_ct0(self, client):
        res = client.post("/start", data={"list_url": "https://x.com/i/lists/123", "auth_token": "x"})
        assert res.status_code == 400

    def test_invalid_list_url(self, client):
        res = client.post("/start", data={
            "list_url": "not-a-list",
            "auth_token": "abc",
            "ct0": "xyz",
        })
        assert res.status_code == 400
        assert b"error" in res.data

    def test_list_url_too_long(self, client):
        res = client.post("/start", data={
            "list_url": "x" * 301,
            "auth_token": "abc",
            "ct0": "xyz",
        })
        assert res.status_code == 400

    def test_auth_token_too_long(self, client):
        res = client.post("/start", data={
            "list_url": "https://x.com/i/lists/123",
            "auth_token": "a" * 201,
            "ct0": "xyz",
        })
        assert res.status_code == 400

    def test_ct0_too_long(self, client):
        res = client.post("/start", data={
            "list_url": "https://x.com/i/lists/123",
            "auth_token": "abc",
            "ct0": "c" * 201,
        })
        assert res.status_code == 400

    def test_valid_start_returns_job_id(self, client):
        with patch("app.run_job"):
            res = client.post("/start", data={
                "list_url": "https://x.com/i/lists/1234567890",
                "auth_token": "a" * 40,
                "ct0": "b" * 40,
            })
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "job_id" in data
        # Must be a valid UUID
        uuid.UUID(data["job_id"])


class TestPoll:
    def test_invalid_uuid_returns_404(self, client):
        res = client.get("/poll/not-a-uuid")
        assert res.status_code == 404

    def test_unknown_job_returns_done(self, client):
        res = client.get(f"/poll/{uuid.uuid4()}")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["done"] is True
        assert data["messages"] == []

    def test_sql_injection_attempt_returns_404(self, client):
        res = client.get("/poll/'; DROP TABLE jobs; --")
        assert res.status_code == 404

    def test_returns_cursor_and_messages(self, client):
        with patch("app.run_job"):
            start_res = client.post("/start", data={
                "list_url": "https://x.com/i/lists/1234567890",
                "auth_token": "a" * 40,
                "ct0": "b" * 40,
            })
        job_id = json.loads(start_res.data)["job_id"]
        res = client.get(f"/poll/{job_id}?cursor=0")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "messages" in data
        assert "cursor" in data
        assert "done" in data


class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        res = client.get("/")
        assert res.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        res = client.get("/")
        assert res.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, client):
        res = client.get("/")
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_csp_present(self, client):
        res = client.get("/")
        assert "Content-Security-Policy" in res.headers

    def test_csp_no_unsafe_inline(self, client):
        res = client.get("/")
        csp = res.headers.get("Content-Security-Policy", "")
        assert "unsafe-inline" not in csp

    def test_csp_frame_ancestors_none(self, client):
        res = client.get("/")
        csp = res.headers.get("Content-Security-Policy", "")
        assert "frame-ancestors 'none'" in csp
