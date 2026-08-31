"""SM Workflow Approval 领域测试：流程定义、提交、多级审批与驳回。"""

import pytest
from fastapi.testclient import TestClient

from app import base
from app.main import VERSION, app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(base, "internal_api_key", lambda: "TEST")
    base.reset_state()
    from app.main import _init as init_db
    init_db()
    with TestClient(app) as c:
        c.headers["X-Internal-Token"] = "TEST"
        yield c


def _definition(client, name="报销审批"):
    return client.post("/api/workflow/definitions", json={"name": name, "steps": ["部门经理", "财务总监"]}).json()["id"]


def _request(client, definition_id, title="报销单"):
    return client.post("/api/workflow/requests", json={"definition_id": definition_id, "title": title, "requester": "张三", "payload": {"amount": 1000}}).json()["id"]


def test_health_and_version(client):
    r = client.get("/health", headers={"X-Request-Id": "suite-test"})
    assert r.status_code == 200
    assert r.json()["version"] == VERSION


def test_definition_lifecycle(client):
    _definition(client)
    assert client.post("/api/workflow/definitions", json={"name": "报销审批", "steps": ["x"]}).status_code == 409
    assert client.get("/api/workflow/definitions").json()["total"] == 1


def test_submit_and_detail(client):
    def_id = _definition(client)
    req_id = _request(client, def_id)
    detail = client.get(f"/api/workflow/requests/{req_id}").json()
    assert detail["status"] == "pending"
    assert len(detail["approvals"]) == 2
    assert client.get("/api/workflow/requests").json()["total"] == 1


def test_multi_step_approve_then_reject(client):
    def_id = _definition(client)
    req_id = _request(client, def_id)
    # 非当前审批人拒绝
    assert client.post(f"/api/workflow/requests/{req_id}/approve", json={"approver": "财务总监"}).status_code == 403
    # 第一级通过 → in-progress
    r1 = client.post(f"/api/workflow/requests/{req_id}/approve", json={"approver": "部门经理", "comment": "同意"})
    assert r1.json()["status"] == "in-progress"
    # 第二级驳回 → rejected
    r2 = client.post(f"/api/workflow/requests/{req_id}/reject", json={"approver": "财务总监", "comment": "金额不符"})
    assert r2.json()["status"] == "rejected"
    assert client.get(f"/api/workflow/requests/{req_id}").json()["approvals"][1]["status"] == "rejected"


def test_full_approve(client):
    def_id = _definition(client)
    req_id = _request(client, def_id)
    client.post(f"/api/workflow/requests/{req_id}/approve", json={"approver": "部门经理"})
    final = client.post(f"/api/workflow/requests/{req_id}/approve", json={"approver": "财务总监"})
    assert final.json()["status"] == "approved"
    # 已结束不可再审批
    assert client.post(f"/api/workflow/requests/{req_id}/approve", json={"approver": "财务总监"}).status_code == 409


def test_missing(client):
    assert client.post("/api/workflow/requests", json={"definition_id": "no-such-def", "title": "tt", "requester": "r"}).status_code == 404
    assert client.get("/api/workflow/requests/nope").status_code == 404


def test_stats(client):
    def_id = _definition(client)
    _request(client, def_id)
    stats = client.get("/api/workflow/stats").json()
    assert stats["pending"] == 1


def test_manifest_and_crypto(client):
    assert client.get("/api/integration/manifest").json()["version"] == VERSION
    enc = client.post("/api/crypto/encrypt", json={"value": "x"}).json()["ciphertext"]
    assert client.post("/api/crypto/decrypt", json={"value": enc}).json()["plaintext"] == "x"


def test_write_requires_auth(client):
    del client.headers["X-Internal-Token"]
    assert client.post("/api/workflow/definitions", json={"name": "d", "steps": ["a"]}).status_code == 401
