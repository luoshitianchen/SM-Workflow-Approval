"""SM Workflow Approval —— 流程审批引擎：流程定义、审批请求、多级审批与驳回。"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from app import base

SERVICE = "sm-workflow-approval"
VERSION = "2.0.0"
NAME = "SM Workflow Approval"
DESCRIPTION = "流程审批引擎：流程定义、审批请求、多级审批与驳回"
PORT = 8350


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _init() -> None:
    with base.db_ctx() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS definitions (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT,
                steps TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY, definition_id TEXT NOT NULL, title TEXT NOT NULL,
                requester TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending', current_step INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY, request_id TEXT NOT NULL, step_index INTEGER NOT NULL,
                approver TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                comment TEXT, decided_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status, created_at DESC);
            """
        )


app = base.create_app(
    service=SERVICE, name=NAME, description=DESCRIPTION, version=VERSION, port=PORT,
    dependencies=["sm-iam", "sm-audit-log-center"],
    events=["workflow.request_submitted", "workflow.approved", "workflow.rejected"],
    overview_fn=lambda _r: {
        "summary": {
            "definitions": base.get_db().execute("SELECT COUNT(*) FROM definitions").fetchone()[0],
            "pending": base.get_db().execute("SELECT COUNT(*) FROM requests WHERE status='pending'").fetchone()[0],
        }
    },
)
_init()


class DefinitionIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=300)
    steps: list[str] = Field(min_length=1, max_length=20)


class RequestIn(BaseModel):
    definition_id: str = Field(min_length=8)
    title: str = Field(min_length=2, max_length=200)
    requester: str = Field(min_length=1, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)


class DecisionIn(BaseModel):
    approver: str = Field(min_length=1, max_length=80)
    comment: str = Field(default="", max_length=500)


@app.get("/api/workflow/definitions")
def list_definitions() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM definitions ORDER BY created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/workflow/definitions", status_code=status.HTTP_201_CREATED)
def create_definition(payload: DefinitionIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    definition_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        try:
            conn.execute("INSERT INTO definitions VALUES (?,?,?,?,?)", (definition_id, payload.name, payload.description, json.dumps(payload.steps, ensure_ascii=False), _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "流程定义已存在") from exc
    return {"id": definition_id, "name": payload.name, "steps": payload.steps}


@app.post("/api/workflow/requests", status_code=status.HTTP_201_CREATED)
def submit_request(payload: RequestIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    request_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        definition = conn.execute("SELECT * FROM definitions WHERE id=?", (payload.definition_id,)).fetchone()
        if not definition:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "流程定义不存在")
        steps = json.loads(definition["steps"])
        conn.execute("INSERT INTO requests (id, definition_id, title, requester, payload, status, current_step, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)", (request_id, payload.definition_id, payload.title, payload.requester, json.dumps(payload.payload, ensure_ascii=False), "pending", 0, _now(), _now()))
        for index, approver in enumerate(steps):
            conn.execute("INSERT INTO approvals (id, request_id, step_index, approver, status, comment, decided_at) VALUES (?,?,?,?,?,?,?)", (str(uuid.uuid4()), request_id, index, approver, "pending", None, None))
        base.record_audit("workflow.request_submitted", payload.requester, f"request={request_id} definition={payload.definition_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": request_id, "status": "pending", "title": payload.title}


@app.get("/api/workflow/requests")
def list_requests(status_: str | None = None) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if status_:
            rows = conn.execute("SELECT * FROM requests WHERE status=? ORDER BY created_at DESC LIMIT 200", (status_,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM requests ORDER BY created_at DESC LIMIT 200").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.get("/api/workflow/requests/{request_id}")
def get_request(request_id: str) -> dict[str, Any]:
    with base.db_ctx() as conn:
        row = conn.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "审批请求不存在")
        approvals = conn.execute("SELECT * FROM approvals WHERE request_id=? ORDER BY step_index", (request_id,)).fetchall()
    return {**dict(row), "approvals": [dict(r) for r in approvals]}


@app.post("/api/workflow/requests/{request_id}/approve")
def approve(request_id: str, payload: DecisionIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    return _decide(request_id, payload, True, request)


@app.post("/api/workflow/requests/{request_id}/reject")
def reject(request_id: str, payload: DecisionIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    return _decide(request_id, payload, False, request)


def _decide(request_id: str, payload: DecisionIn, approved: bool, request: Request) -> dict[str, Any]:
    with base.db_ctx() as conn:
        req = conn.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
        if not req:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "审批请求不存在")
        if req["status"] != "pending":
            raise HTTPException(status.HTTP_409_CONFLICT, "请求已结束，无法审批")
        definition = conn.execute("SELECT * FROM definitions WHERE id=?", (req["definition_id"],)).fetchone()
        steps = json.loads(definition["steps"])
        current = conn.execute("SELECT * FROM approvals WHERE request_id=? AND step_index=? AND status='pending'", (request_id, req["current_step"])).fetchone()
        if not current:
            raise HTTPException(status.HTTP_409_CONFLICT, "当前步骤无待审批项")
        if current["approver"] != payload.approver:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "非当前步骤审批人")
        conn.execute("UPDATE approvals SET status=?, comment=?, decided_at=? WHERE id=?", ("approved" if approved else "rejected", payload.comment, _now(), current["id"]))
        if not approved:
            conn.execute("UPDATE requests SET status='rejected', updated_at=? WHERE id=?", (_now(), request_id))
            conn.execute("UPDATE approvals SET status='skipped' WHERE request_id=? AND status='pending'", (request_id,))
            base.record_audit("workflow.rejected", payload.approver, f"request={request_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
            return {"id": request_id, "status": "rejected"}
        next_step = req["current_step"] + 1
        if next_step >= len(steps):
            conn.execute("UPDATE requests SET status='approved', current_step=?, updated_at=? WHERE id=?", (next_step, _now(), request_id))
            base.record_audit("workflow.approved", payload.approver, f"request={request_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
            return {"id": request_id, "status": "approved"}
        conn.execute("UPDATE requests SET current_step=?, updated_at=? WHERE id=?", (next_step, _now(), request_id))
    return {"id": request_id, "status": "in-progress", "current_step": next_step}


@app.get("/api/workflow/stats")
def stats() -> dict[str, Any]:
    with base.db_ctx() as conn:
        def _count(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]
        return {
            "definitions": _count("SELECT COUNT(*) FROM definitions"),
            "pending": _count("SELECT COUNT(*) FROM requests WHERE status='pending'"),
            "approved": _count("SELECT COUNT(*) FROM requests WHERE status='approved'"),
            "rejected": _count("SELECT COUNT(*) FROM requests WHERE status='rejected'"),
            "total": _count("SELECT COUNT(*) FROM requests"),
        }
