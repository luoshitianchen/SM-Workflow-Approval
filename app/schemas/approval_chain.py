"""审批链 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ApprovalChainStart(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    applicant: str = Field(min_length=1, max_length=128)
    payload: str = Field(default="", max_length=4000)


class ApprovalDecision(BaseModel):
    operator: str = Field(min_length=1, max_length=128)
    comment: str = Field(default="", max_length=1000)


class ApprovalChainItem(BaseModel):
    id: str
    workflow_id: str
    title: str
    applicant: str
    status: str
    current_node_index: int
    payload: str
    created_at: datetime
    updated_at: datetime


class ApprovalChainList(BaseModel):
    total: int
    items: list[ApprovalChainItem]
