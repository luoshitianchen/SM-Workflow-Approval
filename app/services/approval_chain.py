"""审批链服务层：发起、逐级审批、审批人校验与状态流转。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.approval_chain import ApprovalChain
from app.repositories import approval_chain as repo
from app.repositories import workflow as workflow_repo
from app.repositories import workflow_node as node_repo
from app.schemas.approval_chain import ApprovalChainStart
from app.services.audit import record_audit


def _chain_to_dict(c: ApprovalChain) -> dict:
    return {
        "id": c.id, "workflow_id": c.workflow_id, "title": c.title,
        "applicant": c.applicant, "status": c.status,
        "current_node_index": c.current_node_index, "payload": c.payload,
        "created_at": c.created_at.isoformat() if c.created_at else "",
        "updated_at": c.updated_at.isoformat() if c.updated_at else "",
    }


class ChainService:
    @staticmethod
    async def list_chains(session: AsyncSession, limit: int = 100, offset: int = 0,
                          status_filter: str | None = None,
                          workflow_id: str | None = None,
                          applicant: str | None = None,
                          keyword: str | None = None) -> dict:
        items = await repo.list_chains(
            session, limit=limit, offset=offset, status=status_filter,
            workflow_id=workflow_id, applicant=applicant, keyword=keyword,
        )
        total = await repo.count_chains(
            session, status=status_filter, workflow_id=workflow_id,
            applicant=applicant, keyword=keyword,
        )
        return {"total": total, "items": [_chain_to_dict(c) for c in items]}

    @staticmethod
    async def get_chain(session: AsyncSession, chain_id: str) -> dict:
        chain = await repo.get_chain(session, chain_id)
        if not chain:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "审批链不存在")
        data = _chain_to_dict(chain)
        # 附带当前待办节点信息
        nodes = await node_repo.list_nodes(session, chain.workflow_id)
        current = next((n for n in nodes if n.order_index == chain.current_node_index), None)
        data["current_approver"] = current.approver if current and chain.status == "pending" else ""
        return data

    @staticmethod
    async def start_chain(session: AsyncSession, workflow_id: str,
                          payload: ApprovalChainStart, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        workflow = await workflow_repo.get_workflow(session, workflow_id)
        if not workflow:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "流程不存在")
        if workflow.status != "active":
            raise HTTPException(status.HTTP_409_CONFLICT, "仅启用中的流程可发起审批")
        nodes = await node_repo.list_nodes(session, workflow_id)
        approval_nodes = [n for n in nodes if n.node_type == "approval"]
        if not approval_nodes:
            raise HTTPException(status.HTTP_409_CONFLICT, "流程未配置审批节点")
        chain = ApprovalChain(
            id=str(uuid.uuid4()), workflow_id=workflow_id, title=payload.title,
            applicant=payload.applicant, status="pending",
            current_node_index=approval_nodes[0].order_index, payload=payload.payload,
        )
        chain = await repo.create_chain(session, chain)
        await record_audit(session, "chain.started", "internal",
                           f"chain_id={chain.id} applicant={payload.applicant}", request)
        return _chain_to_dict(chain)

    @staticmethod
    async def _resolve_current_node(session: AsyncSession, chain: ApprovalChain):
        nodes = await node_repo.list_nodes(session, chain.workflow_id)
        ordered = [n for n in nodes if n.node_type == "approval"]
        ordered.sort(key=lambda n: n.order_index)
        current = next((n for n in ordered if n.order_index == chain.current_node_index), None)
        return ordered, current

    @staticmethod
    async def approve(session: AsyncSession, chain_id: str, operator: str,
                      request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        chain = await repo.get_chain(session, chain_id)
        if not chain:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "审批链不存在")
        if chain.status != "pending":
            raise HTTPException(status.HTTP_409_CONFLICT, f"当前状态 {chain.status} 不可审批")
        ordered, current = await ChainService._resolve_current_node(session, chain)
        if not current:
            raise HTTPException(status.HTTP_409_CONFLICT, "当前待办节点缺失")
        # 审批人分配校验：仅当前节点审批人可处理
        if current.approver and operator != current.approver:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"仅审批人 {current.approver} 可处理该节点")
        # 是否最后一个审批节点
        is_last = current.order_index == ordered[-1].order_index
        if is_last:
            chain.status = "approved"
        else:
            idx = ordered.index(current)
            chain.current_node_index = ordered[idx + 1].order_index
        chain = await repo.update_chain(session, chain)
        await record_audit(session, "chain.approved", "internal",
                           f"chain_id={chain_id} operator={operator}", request)
        return _chain_to_dict(chain)

    @staticmethod
    async def reject(session: AsyncSession, chain_id: str, operator: str,
                     request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        chain = await repo.get_chain(session, chain_id)
        if not chain:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "审批链不存在")
        if chain.status != "pending":
            raise HTTPException(status.HTTP_409_CONFLICT, f"当前状态 {chain.status} 不可驳回")
        ordered, current = await ChainService._resolve_current_node(session, chain)
        if not current:
            raise HTTPException(status.HTTP_409_CONFLICT, "当前待办节点缺失")
        if current.approver and operator != current.approver:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"仅审批人 {current.approver} 可处理该节点")
        chain.status = "rejected"
        chain = await repo.update_chain(session, chain)
        await record_audit(session, "chain.rejected", "internal",
                           f"chain_id={chain_id} operator={operator}", request)
        return _chain_to_dict(chain)
