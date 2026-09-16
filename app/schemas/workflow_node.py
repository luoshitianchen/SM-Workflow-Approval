"""流程节点 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WorkflowNodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    order_index: int = Field(ge=1, le=100)
    node_type: Literal["approval", "cc"] = "approval"
    approver: str = Field(default="", max_length=128)


class WorkflowNodeItem(BaseModel):
    id: str
    workflow_id: str
    name: str
    order_index: int
    node_type: str
    approver: str
    created_at: datetime


class WorkflowNodeList(BaseModel):
    total: int
    items: list[WorkflowNodeItem]
