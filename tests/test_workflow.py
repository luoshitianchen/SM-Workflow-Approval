"""Workflow-Approval 业务深化测试：流程 / 节点 / 审批链。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

INTERNAL_TOKEN = "test-internal-key-12345"
AUTH_HEADERS = {"X-Internal-Token": INTERNAL_TOKEN}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _create_workflow(client, code: str) -> str:
    resp = client.post("/api/wf/workflows", json={
        "name": f"流程 {code}", "code": code, "description": "测试流程",
    }, headers=AUTH_HEADERS)
    return resp.json()["id"]


# ═══════════════════════════════════════════════════════════
# 流程定义
# ═══════════════════════════════════════════════════════════
class TestWorkflowManagement:
    def test_create_workflow_success(self, client):
        resp = client.post("/api/wf/workflows", json={
            "name": "请假审批", "code": "WF-LEAVE", "description": "员工请假",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "draft"
        assert data["code"] == "WF-LEAVE"

    def test_create_workflow_duplicate_code(self, client):
        resp = client.post("/api/wf/workflows", json={
            "name": "重复", "code": "WF-LEAVE",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_create_workflow_requires_token(self, client):
        resp = client.post("/api/wf/workflows", json={
            "name": "无令牌", "code": "WF-NONE",
        })
        assert resp.status_code in (401, 403)

    def test_list_workflows(self, client):
        resp = client.get("/api/wf/workflows", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_get_workflow(self, client):
        list_resp = client.get("/api/wf/workflows?keyword=LEAVE", headers=AUTH_HEADERS)
        wid = list_resp.json()["items"][0]["id"]
        resp = client.get(f"/api/wf/workflows/{wid}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["code"] == "WF-LEAVE"

    def test_get_workflow_not_found(self, client):
        resp = client.get("/api/wf/workflows/nonexistent", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_activate_without_nodes_rejected(self, client):
        wid = _create_workflow(client, "WF-NO-NODES")
        resp = client.patch(f"/api/wf/workflows/{wid}", json={"status": "active"}, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_update_workflow_name(self, client):
        wid = _create_workflow(client, "WF-UPD")
        resp = client.patch(f"/api/wf/workflows/{wid}", json={"name": "更新后流程"}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["name"] == "更新后流程"


# ═══════════════════════════════════════════════════════════
# 流程节点
# ═══════════════════════════════════════════════════════════
class TestNodeManagement:
    def test_add_node_success(self, client):
        wid = _create_workflow(client, "WF-NODE-OK")
        resp = client.post(f"/api/wf/workflows/{wid}/nodes", json={
            "name": "主管审批", "order_index": 1, "node_type": "approval", "approver": "bob",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["approver"] == "bob"
        assert resp.json()["order_index"] == 1

    def test_add_node_missing_approver_rejected(self, client):
        wid = _create_workflow(client, "WF-NODE-NOAPPR")
        resp = client.post(f"/api/wf/workflows/{wid}/nodes", json={
            "name": "缺审批人", "order_index": 1, "node_type": "approval",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 400

    def test_add_node_duplicate_order_rejected(self, client):
        wid = _create_workflow(client, "WF-NODE-DUP")
        client.post(f"/api/wf/workflows/{wid}/nodes", json={
            "name": "第一节点", "order_index": 1, "approver": "bob",
        }, headers=AUTH_HEADERS)
        resp = client.post(f"/api/wf/workflows/{wid}/nodes", json={
            "name": "顺序重复", "order_index": 1, "approver": "alice",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_list_nodes(self, client):
        wid = _create_workflow(client, "WF-NODE-LIST")
        client.post(f"/api/wf/workflows/{wid}/nodes", json={
            "name": "节点1", "order_index": 1, "approver": "bob",
        }, headers=AUTH_HEADERS)
        resp = client.get(f"/api/wf/workflows/{wid}/nodes", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_nodes_nonexistent_workflow(self, client):
        resp = client.get("/api/wf/workflows/nonexistent/nodes", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_delete_node(self, client):
        wid = _create_workflow(client, "WF-NODE-DEL")
        create_resp = client.post(f"/api/wf/workflows/{wid}/nodes", json={
            "name": "待删节点", "order_index": 1, "approver": "bob",
        }, headers=AUTH_HEADERS)
        node_id = create_resp.json()["id"]
        resp = client.delete(f"/api/wf/nodes/{node_id}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════════════════
# 审批链
# ═══════════════════════════════════════════════════════════
class TestApprovalChain:
    def _setup_two_level(self, client, code: str) -> str:
        """创建并启用一个两级审批流程，返回 workflow_id。"""
        wid = _create_workflow(client, code)
        client.post(f"/api/wf/workflows/{wid}/nodes", json={
            "name": "主管", "order_index": 1, "approver": "bob",
        }, headers=AUTH_HEADERS)
        client.post(f"/api/wf/workflows/{wid}/nodes", json={
            "name": "总监", "order_index": 2, "approver": "alice",
        }, headers=AUTH_HEADERS)
        client.patch(f"/api/wf/workflows/{wid}", json={"status": "active"}, headers=AUTH_HEADERS)
        return wid

    def test_start_chain_on_draft_rejected(self, client):
        wid = _create_workflow(client, "WF-CHAIN-DRAFT")
        resp = client.post(f"/api/wf/workflows/{wid}/chains", json={
            "title": "草稿流程审批", "applicant": "zhangsan",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_start_chain_success(self, client):
        wid = self._setup_two_level(client, "WF-CHAIN-OK")
        resp = client.post(f"/api/wf/workflows/{wid}/chains", json={
            "title": "请假三天", "applicant": "zhangsan", "payload": "事由：回家",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["current_node_index"] == 1

    def test_start_chain_nonexistent_workflow(self, client):
        resp = client.post("/api/wf/workflows/nonexistent/chains", json={
            "title": "孤儿审批", "applicant": "x",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_full_approve_flow(self, client):
        wid = self._setup_two_level(client, "WF-CHAIN-FULL")
        start = client.post(f"/api/wf/workflows/{wid}/chains", json={
            "title": "采购申请", "applicant": "lisi",
        }, headers=AUTH_HEADERS)
        chain_id = start.json()["id"]
        # 错误审批人 -> 403
        bad = client.post(f"/api/wf/chains/{chain_id}/approve",
                          json={"operator": "stranger"}, headers=AUTH_HEADERS)
        assert bad.status_code == 403
        # bob 通过第一级 -> 推进到第二级
        r1 = client.post(f"/api/wf/chains/{chain_id}/approve",
                         json={"operator": "bob"}, headers=AUTH_HEADERS)
        assert r1.status_code == 200
        assert r1.json()["status"] == "pending"
        assert r1.json()["current_node_index"] == 2
        # alice 通过第二级 -> 完成
        r2 = client.post(f"/api/wf/chains/{chain_id}/approve",
                         json={"operator": "alice"}, headers=AUTH_HEADERS)
        assert r2.status_code == 200
        assert r2.json()["status"] == "approved"

    def test_reject_flow(self, client):
        wid = self._setup_two_level(client, "WF-CHAIN-REJ")
        start = client.post(f"/api/wf/workflows/{wid}/chains", json={
            "title": "加班申请", "applicant": "wangwu",
        }, headers=AUTH_HEADERS)
        chain_id = start.json()["id"]
        r = client.post(f"/api/wf/chains/{chain_id}/reject",
                        json={"operator": "bob", "comment": "材料不全"}, headers=AUTH_HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_approve_terminal_chain_rejected(self, client):
        wid = self._setup_two_level(client, "WF-CHAIN-TERM")
        start = client.post(f"/api/wf/workflows/{wid}/chains", json={
            "title": "终态审批", "applicant": "zhaoliu",
        }, headers=AUTH_HEADERS)
        chain_id = start.json()["id"]
        # 直接驳回成终态
        client.post(f"/api/wf/chains/{chain_id}/reject",
                    json={"operator": "bob"}, headers=AUTH_HEADERS)
        again = client.post(f"/api/wf/chains/{chain_id}/approve",
                            json={"operator": "alice"}, headers=AUTH_HEADERS)
        assert again.status_code == 409

    def test_list_chains_filter_status(self, client):
        resp = client.get("/api/wf/chains?status=approved", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "approved"

    def test_list_chains_filter_applicant(self, client):
        resp = client.get("/api/wf/chains?applicant=lisi", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1
        for item in resp.json()["items"]:
            assert item["applicant"] == "lisi"

    def test_get_chain_shows_current_approver(self, client):
        wid = self._setup_two_level(client, "WF-CHAIN-CUR")
        start = client.post(f"/api/wf/workflows/{wid}/chains", json={
            "title": "当前审批人查询", "applicant": "chenqi",
        }, headers=AUTH_HEADERS)
        chain_id = start.json()["id"]
        resp = client.get(f"/api/wf/chains/{chain_id}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["current_approver"] == "bob"

    def test_get_chain_not_found(self, client):
        resp = client.get("/api/wf/chains/nonexistent", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_chain_requires_token(self, client):
        wid = self._setup_two_level(client, "WF-CHAIN-NOAUTH")
        resp = client.post(f"/api/wf/workflows/{wid}/chains", json={
            "title": "无令牌审批", "applicant": "x",
        })
        assert resp.status_code in (401, 403)
