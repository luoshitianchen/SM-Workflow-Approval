"""审批链路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.approval_chain import ApprovalChainStart, ApprovalDecision
from app.services.approval_chain import ChainService

router = APIRouter(prefix="/api/wf", tags=["wf-chains"])


@router.post("/workflows/{workflow_id}/chains", status_code=status.HTTP_201_CREATED)
async def start_chain(
    workflow_id: str, payload: ApprovalChainStart, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ChainService.start_chain(session, workflow_id, payload, request)


@router.get("/chains")
async def list_chains(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    workflow_id: str | None = Query(default=None),
    applicant: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ChainService.list_chains(
        session, limit=limit, offset=offset, status_filter=status_filter,
        workflow_id=workflow_id, applicant=applicant, keyword=keyword,
    )


@router.get("/chains/{chain_id}")
async def get_chain(
    chain_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ChainService.get_chain(session, chain_id)


@router.post("/chains/{chain_id}/approve")
async def approve(
    chain_id: str, payload: ApprovalDecision, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ChainService.approve(session, chain_id, payload.operator, request)


@router.post("/chains/{chain_id}/reject")
async def reject(
    chain_id: str, payload: ApprovalDecision, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ChainService.reject(session, chain_id, payload.operator, request)
