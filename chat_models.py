"""Pydantic models for chat endpoints and internal data structures.

This module defines request and response models, history containers, and
error shapes with strong validation and helpful docstrings.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, RootModel, ValidationError, validator


class ChatMessage(BaseModel):
    """A single chat message belonging to a conversation.

    Fields:
        role: 'user' | 'assistant' | 'system'
        text: message text (non-empty, max length enforced)
        meta: optional dictionary with auxiliary metadata
    """

    role: str = Field(..., description="Message role: user, assistant, or system")
    text: str = Field(..., min_length=1, max_length=20000, description="Message text")
    meta: Optional[Dict[str, Any]] = Field(None, description="Optional metadata for the message")

    @validator("role")
    def role_must_be_known(cls, v: str) -> str:
        allowed = {"user", "assistant", "system"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v_lower


class ChatRequest(BaseModel):
    """Request model for sending a new chat message or starting a conversation.

    Fields:
        session_id: optional session identifier. If omitted, a new session may be created.
        message: the user's message payload
        provider: optional provider preference ('openai' or 'gemini')
        max_tokens: optional override for max response tokens
    """

    session_id: Optional[str] = Field(None, description="Existing session id (optional)")
    message: ChatMessage = Field(..., description="User message payload")
    provider: Optional[str] = Field(None, description="Provider preference: openai or gemini")
    max_tokens: Optional[int] = Field(None, ge=1, le=100000, description="Max tokens to request from the model")

    @validator("provider")
    def provider_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"openai", "gemini"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"provider must be one of {allowed}")
        return v_lower


class ChatResponse(BaseModel):
    """Standardized response returned after generating a reply.

    Fields:
        ok: whether the response was successful
        provider: which LLM provider produced the reply
        model: the model used
        text: the assistant's reply
        raw: optional raw provider response
        error: optional error string when ok is false
    """

    ok: bool = Field(..., description="Whether the request succeeded")
    provider: Optional[str] = Field(None, description="Provider used for reply")
    model: Optional[str] = Field(None, description="Model used")
    text: Optional[str] = Field(None, description="Assistant text")
    raw: Optional[Dict[str, Any]] = Field(None, description="Raw provider response")
    error: Optional[str] = Field(None, description="Error message if any")


class ConversationHistory(BaseModel):
    """Represents the full history of a conversation session.

    Fields:
        session_id: id of the session
        system_prompt: optional system prompt used at session creation
        messages: ordered list of messages (user/assistant/system)
    """

    session_id: str = Field(..., description="Session identifier")
    system_prompt: Optional[str] = Field(None, description="System prompt for the session")
    messages: List[ChatMessage] = Field(default_factory=list, description="Ordered message list")

    @validator("messages", pre=True)
    def ensure_messages_list(cls, v):
        if v is None:
            return []
        return v


class ChatError(BaseModel):
    """Error model for API failures or validation errors.

    Fields:
        code: machine-readable error code
        message: human-readable message
        details: optional details (e.g., validation errors)
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Any] = Field(None, description="Optional details / validation info")


__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ConversationHistory",
    "ChatError",
]
