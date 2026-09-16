"""流程定义 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    description: str = Field(default="", max_length=2000)


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: Literal["draft", "active", "disabled"] | None = None


class WorkflowResponse(BaseModel):
    id: str
    name: str
    code: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    total: int
    items: list[WorkflowResponse]
