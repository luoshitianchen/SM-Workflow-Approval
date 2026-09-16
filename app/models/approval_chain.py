"""审批链实例模型：流程的一次实际审批。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class ApprovalChain(Base):
    """审批链实例：在某流程上发起的一条审批流。"""

    __tablename__ = "wf_chains"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    applicant: Mapped[str] = mapped_column(String(128), default="", index=True)
    # 状态：pending / approved / rejected / cancelled
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # 当前节点顺序号（从 1 开始）
    current_node_index: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
