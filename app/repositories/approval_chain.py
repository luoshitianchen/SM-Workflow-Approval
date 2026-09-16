"""审批链实例仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_chain import ApprovalChain


async def get_chain(session: AsyncSession, chain_id: str) -> ApprovalChain | None:
    result = await session.execute(select(ApprovalChain).where(ApprovalChain.id == chain_id))
    return result.scalar_one_or_none()


async def list_chains(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    status: str | None = None,
    workflow_id: str | None = None,
    applicant: str | None = None,
    keyword: str | None = None,
) -> list[ApprovalChain]:
    stmt = select(ApprovalChain).order_by(ApprovalChain.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(ApprovalChain.status == status)
    if workflow_id:
        stmt = stmt.where(ApprovalChain.workflow_id == workflow_id)
    if applicant:
        stmt = stmt.where(ApprovalChain.applicant == applicant)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(ApprovalChain.title.like(like))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_chains(
    session: AsyncSession,
    status: str | None = None,
    workflow_id: str | None = None,
    applicant: str | None = None,
    keyword: str | None = None,
) -> int:
    stmt = select(func.count(ApprovalChain.id))
    if status:
        stmt = stmt.where(ApprovalChain.status == status)
    if workflow_id:
        stmt = stmt.where(ApprovalChain.workflow_id == workflow_id)
    if applicant:
        stmt = stmt.where(ApprovalChain.applicant == applicant)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(ApprovalChain.title.like(like))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_chain(session: AsyncSession, chain: ApprovalChain) -> ApprovalChain:
    session.add(chain)
    await session.commit()
    await session.refresh(chain)
    return chain


async def update_chain(session: AsyncSession, chain: ApprovalChain) -> ApprovalChain:
    await session.commit()
    await session.refresh(chain)
    return chain
