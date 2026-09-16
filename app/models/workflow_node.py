"""流程节点模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class WorkflowNode(Base):
    """流程节点：定义某一步审批人与顺序。"""

    __tablename__ = "wf_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # 顺序号，从 1 开始，同一流程内唯一
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # 节点类型：approval（审批）/ cc（抄送）
    node_type: Mapped[str] = mapped_column(String(16), default="approval")
    approver: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
