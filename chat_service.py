"""Chat service managing conversation sessions and history.

This module provides an in-memory ChatService with session creation,
history retrieval, conversation clearing, export functionality, and
integration with the LLMService for generating replies. It also supports
resume-based context for personalized AI assistant capabilities.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.llm_service import LLMService, LLMResponse
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str  # 'user' or 'assistant' or 'system'
    content: str
    meta: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        # Ensure role is one of the valid OpenAI roles
        if self.role not in ["system", "user", "assistant"]:
            self.role = "user" if self.role == "human" else "assistant"


class ChatSession:
    def __init__(self, session_id: Optional[str] = None, system_prompt: Optional[str] = None):
        self.id = session_id or str(uuid.uuid4())
        self.system_prompt = system_prompt
        self.history: List[Message] = []

    def append(self, role: str, text: str, meta: Optional[Dict[str, Any]] = None) -> None:
        # Validate role
        if role not in ["system", "user", "assistant"]:
            role = "user" if role == "human" else "assistant"
        # Append message with validated role
        self.history.append(Message(role=role, content=text, meta=meta))

    def clear(self) -> None:
        self.history.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "system_prompt": self.system_prompt, "history": [asdict(m) for m in self.history]}


class ChatService:
    """Manage multiple chat sessions and produce LLM replies.

    This implementation stores sessions in memory. For production use,
    swap the storage to a database or cache (Redis) implementation.
    
    Features:
    - Resume-based context injection for personalized responses
    - Multiple session management
    - Conversation history tracking
    """

    def __init__(self, settings=None, llm_service: Optional[LLMService] = None):
        self.settings = settings or get_settings()
        self.llm = llm_service or LLMService(settings=self.settings)
        self._sessions: Dict[str, ChatSession] = {}
        self._lock = asyncio.Lock()
        
        # Load resume content for context injection
        self._resume_context = self._load_resume()
        if self._resume_context:
            logger.info("Resume context loaded successfully")
        else:
            logger.warning("No resume found - chatbot will work without resume context")

    def _load_resume(self) -> str:
        """Load resume content from the data directory."""
        resume_path = Path("data/resume.txt")
        
        if resume_path.exists():
            try:
                content = resume_path.read_text(encoding="utf-8")
                logger.info(f"Loaded resume from {resume_path}")
                return content
            except Exception as e:
                logger.error(f"Failed to load resume: {e}")
                return ""
        else:
            logger.debug(f"Resume file not found at {resume_path}")
            return ""

    async def create_session(self, system_prompt: Optional[str] = None, use_resume_context: bool = True) -> str:
        """Create a new chat session with optional resume context.
        
        Args:
            system_prompt: Custom system prompt (optional)
            use_resume_context: Whether to include resume in the context (default: True)
        
        Returns:
            session_id: The unique identifier for the created session
        """
        # Build enhanced system prompt with resume context
        if use_resume_context and self._resume_context:
            enhanced_prompt = f"""You are a helpful AI assistant. You can answer ANY question the user asks.

IMPORTANT: I have Dheeraj Atmakuri's resume available, but ONLY mention it when specifically asked about Dheeraj or "the candidate".

Resume (for reference):
---
{self._resume_context}
---

RULES:
1. If asked about Dheeraj/candidate (e.g., "What's Dheeraj's experience?", "Tell me about the candidate's skills"):
   → Use the resume above to answer

2. For ALL other questions (cooking, coding, explanations, general knowledge, technical concepts, etc.):
   → Answer normally WITHOUT mentioning the resume or Dheeraj at all
   → Just provide helpful, accurate information like a normal AI assistant

3. NEVER say "I don't have information about X" or "not in the resume" unless the question is specifically about Dheeraj

Examples:
- "How to make paneer biryani?" → Provide cooking instructions (DO NOT mention resume!)
- "Explain AWS Lambda" → Explain the concept (DO NOT mention resume!)
- "What's Dheeraj's experience?" → Use resume to answer
- "Write Python code" → Provide code (DO NOT mention resume!)

{system_prompt if system_prompt else ''}"""
        else:
            enhanced_prompt = system_prompt or "You are a helpful AI assistant."
        
        session = ChatSession(system_prompt=enhanced_prompt)
        async with self._lock:
            self._sessions[session.id] = session
        logger.debug("Created session", extra={"session_id": session.id, "resume_context": bool(self._resume_context)})
        return session.id

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    async def append_user_message(self, session_id: str, text: str, meta: Optional[Dict[str, Any]] = None) -> None:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError("session not found")
        session.append("user", text, meta=meta)

    async def generate_reply(self, session_id: str, provider: Optional[str] = None, timeout: Optional[float] = None) -> LLMResponse:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError("session not found")

        # build messages array for the LLM
        try:
            # Format messages properly for the API
            messages = []
            if session.system_prompt:
                messages.append({"role": "system", "content": session.system_prompt})
            
            # Add validated history messages
            logger.debug(f"Session history length: {len(session.history)}")
            for msg in session.history:
                logger.debug(f"Processing message: {msg}, has role: {hasattr(msg, 'role')}, has content: {hasattr(msg, 'content')}")
                if not hasattr(msg, 'role') or not hasattr(msg, 'content'):
                    logger.warning(f"Invalid message format in history: {msg}")
                    continue
                messages.append({"role": msg.role, "content": msg.content})

            if not messages:
                logger.error(f"No valid messages generated. Session history: {session.history}")
                raise ValueError("No valid messages to send to LLM")

            logger.debug(f"Sending {len(messages)} messages to LLM with provider {provider}: {messages}")
            resp = await self.llm.complete(messages, provider=provider)
            
            if resp.ok and resp.text:
                session.append("assistant", resp.text)
            else:
                error_msg = f"LLM error: {resp.error}"
                logger.warning(error_msg, extra={"session": session_id})
                raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"Failed to generate reply: {str(e)}", extra={"session": session_id})
            # Return an error response with proper model info
            model = self.settings.openai_model if provider == "openai" else self.settings.gemini_model
            return LLMResponse(ok=False, provider=provider or "unknown", model=model or "unknown", error=str(e))

        return resp

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError("session not found")
        return [asdict(m) for m in session.history]

    async def clear_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError("session not found")
        session.clear()

    async def export_session(self, session_id: str, path: Optional[str] = None) -> str:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError("session not found")
        data = session.to_dict()
        if path is None:
            path = f"chat_session_{session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    async def list_sessions(self) -> List[Dict[str, Any]]:
        return [{"id": s.id, "system_prompt": s.system_prompt, "size": len(s.history)} for s in self._sessions.values()]

    async def shutdown(self) -> None:
        await self.llm.close()


__all__ = ["ChatService", "ChatSession", "Message"]
