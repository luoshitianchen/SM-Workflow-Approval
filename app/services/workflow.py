"""流程定义服务层：CRUD 与启用校验。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.workflow import Workflow
from app.repositories import workflow as repo
from app.repositories import workflow_node as node_repo
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.services.audit import record_audit


def _wf_to_dict(w: Workflow) -> dict:
    return {
        "id": w.id, "name": w.name, "code": w.code, "description": w.description,
        "status": w.status,
        "created_at": w.created_at.isoformat() if w.created_at else "",
        "updated_at": w.updated_at.isoformat() if w.updated_at else "",
    }


class WorkflowService:
    @staticmethod
    async def list_workflows(session: AsyncSession, limit: int = 100, offset: int = 0,
                             status_filter: str | None = None,
                             keyword: str | None = None) -> dict:
        items = await repo.list_workflows(session, limit=limit, offset=offset,
                                          status=status_filter, keyword=keyword)
        total = await repo.count_workflows(session, status=status_filter, keyword=keyword)
        return {"total": total, "items": [_wf_to_dict(w) for w in items]}

    @staticmethod
    async def get_workflow(session: AsyncSession, workflow_id: str) -> dict:
        workflow = await repo.get_workflow(session, workflow_id)
        if not workflow:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "流程不存在")
        return _wf_to_dict(workflow)

    @staticmethod
    async def create_workflow(session: AsyncSession, payload: WorkflowCreate,
                              request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if await repo.get_workflow_by_code(session, payload.code):
            raise HTTPException(status.HTTP_409_CONFLICT, "流程编码已存在")
        workflow = Workflow(
            id=str(uuid.uuid4()), name=payload.name, code=payload.code,
            description=payload.description, status="draft",
        )
        workflow = await repo.create_workflow(session, workflow)
        await record_audit(session, "workflow.created", "internal",
                           f"code={payload.code}", request)
        return _wf_to_dict(workflow)

    @staticmethod
    async def update_workflow(session: AsyncSession, workflow_id: str, payload: WorkflowUpdate,
                              request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        workflow = await repo.get_workflow(session, workflow_id)
        if not workflow:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "流程不存在")
        if payload.name is not None:
            workflow.name = payload.name
        if payload.description is not None:
            workflow.description = payload.description
        if payload.status is not None:
            # 启用前必须至少配置一个审批节点
            if payload.status == "active":
                nodes = await node_repo.list_nodes(session, workflow_id)
                if not any(n.node_type == "approval" for n in nodes):
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        "流程启用前至少需要一个审批节点",
                    )
            workflow.status = payload.status
        workflow = await repo.update_workflow(session, workflow)
        await record_audit(session, "workflow.updated", "internal",
                           f"workflow_id={workflow_id}", request)
        return _wf_to_dict(workflow)

    @staticmethod
    async def delete_workflow(session: AsyncSession, workflow_id: str,
                              request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        workflow = await repo.get_workflow(session, workflow_id)
        if not workflow:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "流程不存在")
        code = workflow.code
        await repo.delete_workflow(session, workflow)
        await record_audit(session, "workflow.deleted", "internal",
                           f"workflow_id={workflow_id} code={code}", request)
        return {"deleted": True, "id": workflow_id}
