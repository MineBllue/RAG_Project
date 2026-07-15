"""
用户认证功能测试
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAuth:
    def test_get_captcha(self):
        resp = client.get("/api/auth/captcha")
        assert resp.status_code == 200
        data = resp.json()
        assert "captcha_key" in data
        assert "captcha_image" in data

    def test_register_missing_fields(self):
        resp = client.post("/api/auth/register", json={})
        assert resp.status_code == 422

    def test_login_missing_fields(self):
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 422

    def test_password_mismatch(self):
        resp = client.post("/api/auth/register", json={
            "username": "test",
            "password": "123456",
            "confirm_password": "654321",
            "captcha_key": "invalid",
            "captcha_code": "0000",
        })
        assert resp.status_code == 400
        assert "不一致" in resp.json()["detail"]

    def test_health_check(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
