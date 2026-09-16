"""流程节点服务层：节点顺序校验与审批人分配。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.workflow_node import WorkflowNode
from app.repositories import workflow as workflow_repo
from app.repositories import workflow_node as repo
from app.schemas.workflow_node import WorkflowNodeCreate
from app.services.audit import record_audit


def _node_to_dict(n: WorkflowNode) -> dict:
    return {
        "id": n.id, "workflow_id": n.workflow_id, "name": n.name,
        "order_index": n.order_index, "node_type": n.node_type,
        "approver": n.approver,
        "created_at": n.created_at.isoformat() if n.created_at else "",
    }


class NodeService:
    @staticmethod
    async def list_nodes(session: AsyncSession, workflow_id: str) -> dict:
        workflow = await workflow_repo.get_workflow(session, workflow_id)
        if not workflow:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "流程不存在")
        nodes = await repo.list_nodes(session, workflow_id)
        return {"total": len(nodes), "items": [_node_to_dict(n) for n in nodes]}

    @staticmethod
    async def create_node(session: AsyncSession, workflow_id: str,
                           payload: WorkflowNodeCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        workflow = await workflow_repo.get_workflow(session, workflow_id)
        if not workflow:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "流程不存在")
        # 节点顺序校验：同一流程内 order_index 不可重复
        if await repo.get_node_by_order(session, workflow_id, payload.order_index):
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"顺序号 {payload.order_index} 已被占用")
        # 审批节点必须指定审批人
        if payload.node_type == "approval" and not payload.approver:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "审批节点必须指定审批人")
        node = WorkflowNode(
            id=str(uuid.uuid4()), workflow_id=workflow_id, name=payload.name,
            order_index=payload.order_index, node_type=payload.node_type,
            approver=payload.approver,
        )
        node = await repo.create_node(session, node)
        await record_audit(session, "node.created", "internal",
                           f"workflow_id={workflow_id} order={payload.order_index}", request)
        return _node_to_dict(node)

    @staticmethod
    async def delete_node(session: AsyncSession, node_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        node = await repo.get_node(session, node_id)
        if not node:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "节点不存在")
        workflow_id = node.workflow_id
        await repo.delete_node(session, node)
        await record_audit(session, "node.deleted", "internal",
                           f"node_id={node_id} workflow_id={workflow_id}", request)
        return {"deleted": True, "id": node_id}
