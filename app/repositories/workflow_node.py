"""流程节点仓储层。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_node import WorkflowNode


async def get_node(session: AsyncSession, node_id: str) -> WorkflowNode | None:
    result = await session.execute(select(WorkflowNode).where(WorkflowNode.id == node_id))
    return result.scalar_one_or_none()


async def get_node_by_order(session: AsyncSession, workflow_id: str,
                            order_index: int) -> WorkflowNode | None:
    result = await session.execute(
        select(WorkflowNode).where(
            WorkflowNode.workflow_id == workflow_id,
            WorkflowNode.order_index == order_index,
        )
    )
    return result.scalar_one_or_none()


async def list_nodes(session: AsyncSession, workflow_id: str) -> list[WorkflowNode]:
    result = await session.execute(
        select(WorkflowNode)
        .where(WorkflowNode.workflow_id == workflow_id)
        .order_by(WorkflowNode.order_index.asc())
    )
    return list(result.scalars().all())


async def create_node(session: AsyncSession, node: WorkflowNode) -> WorkflowNode:
    session.add(node)
    await session.commit()
    await session.refresh(node)
    return node


async def delete_node(session: AsyncSession, node: WorkflowNode) -> None:
    await session.delete(node)
    await session.commit()
