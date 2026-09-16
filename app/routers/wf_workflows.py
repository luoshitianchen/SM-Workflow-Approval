"""流程定义管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.services.workflow import WorkflowService

router = APIRouter(prefix="/api/wf/workflows", tags=["wf-workflows"])


@router.get("")
async def list_workflows(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await WorkflowService.list_workflows(
        session, limit=limit, offset=offset, status_filter=status_filter, keyword=keyword,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await WorkflowService.create_workflow(session, payload, request)


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await WorkflowService.get_workflow(session, workflow_id)


@router.patch("/{workflow_id}")
async def update_workflow(
    workflow_id: str, payload: WorkflowUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await WorkflowService.update_workflow(session, workflow_id, payload, request)


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await WorkflowService.delete_workflow(session, workflow_id, request)
