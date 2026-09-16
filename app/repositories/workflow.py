"""流程定义仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow


async def get_workflow(session: AsyncSession, workflow_id: str) -> Workflow | None:
    result = await session.execute(select(Workflow).where(Workflow.id == workflow_id))
    return result.scalar_one_or_none()


async def get_workflow_by_code(session: AsyncSession, code: str) -> Workflow | None:
    result = await session.execute(select(Workflow).where(Workflow.code == code))
    return result.scalar_one_or_none()


async def list_workflows(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    status: str | None = None,
    keyword: str | None = None,
) -> list[Workflow]:
    stmt = select(Workflow).order_by(Workflow.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Workflow.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Workflow.name.like(like), Workflow.code.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_workflows(session: AsyncSession, status: str | None = None,
                          keyword: str | None = None) -> int:
    stmt = select(func.count(Workflow.id))
    if status:
        stmt = stmt.where(Workflow.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Workflow.name.like(like), Workflow.code.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_workflow(session: AsyncSession, workflow: Workflow) -> Workflow:
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)
    return workflow


async def update_workflow(session: AsyncSession, workflow: Workflow) -> Workflow:
    await session.commit()
    await session.refresh(workflow)
    return workflow


async def delete_workflow(session: AsyncSession, workflow: Workflow) -> None:
    await session.delete(workflow)
    await session.commit()
