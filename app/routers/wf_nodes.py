"""流程节点管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.workflow_node import WorkflowNodeCreate
from app.services.workflow_node import NodeService

router = APIRouter(prefix="/api/wf", tags=["wf-nodes"])


@router.get("/workflows/{workflow_id}/nodes")
async def list_nodes(
    workflow_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await NodeService.list_nodes(session, workflow_id)


@router.post("/workflows/{workflow_id}/nodes", status_code=status.HTTP_201_CREATED)
async def create_node(
    workflow_id: str, payload: WorkflowNodeCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await NodeService.create_node(session, workflow_id, payload, request)


@router.delete("/nodes/{node_id}")
async def delete_node(
    node_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await NodeService.delete_node(session, node_id, request)
