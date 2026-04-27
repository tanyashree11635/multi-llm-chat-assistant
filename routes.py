"""FastAPI routes for chat operations and conversation management.

Endpoints:
 - POST /chat        : send a message and get a reply
 - POST /sessions    : create a session
 - GET  /sessions    : list sessions
 - GET  /sessions/{id}/history : get session history
 - DELETE /sessions/{id}      : clear session
 - POST /sessions/{id}/export : export session to JSON file
 - GET /health       : basic health check
 - GET /models       : list available/default model info
"""
from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
from typing import Dict, List

from src.models.chat_models import (
	ChatRequest,
	ChatResponse,
	ConversationHistory,
	ChatError,
)
from src.services.chat_service import ChatService

router = APIRouter()
app = FastAPI(title="LLM Chat API", version="0.1")


# --- Logging setup ---
logger = logging.getLogger("llm_chat_api")
if not logger.handlers:
	handler = logging.StreamHandler()
	formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	logger.setLevel(logging.INFO)


# --- Middleware: CORS ---
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # adjust in production
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
	allow_headers=["*"],
)


# --- Simple in-memory rate limiter middleware ---
class RateLimitMiddleware(BaseHTTPMiddleware):
	"""A simple sliding-window rate limiter per-client IP.

	This is intentionally basic for example/demo use. For production use a
	distributed store (Redis) or a mature library (limits/slowapi).
	"""

	def __init__(self, app: ASGIApp, max_requests: int = 60, window_seconds: int = 60):
		super().__init__(app)
		self.max_requests = max_requests
		self.window = window_seconds
		self.storage: Dict[str, List[float]] = {}

	async def dispatch(self, request: Request, call_next):
		# get client ip
		client = request.client.host if request.client else "unknown"
		now = time.time()
		q = self.storage.get(client)
		if q is None:
			q = []
			self.storage[client] = q

		# drop old timestamps
		while q and q[0] <= now - self.window:
			q.pop(0)

		if len(q) >= self.max_requests:
			logger.warning("Rate limit exceeded", extra={"client": client})
			payload = ChatError(code="rate_limited", message="Too many requests", details={"limit": self.max_requests})
			return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content=payload.model_dump())

		q.append(now)
		return await call_next(request)


app.add_middleware(RateLimitMiddleware, max_requests=120, window_seconds=60)


# --- Security headers middleware ---
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
	response: Response = await call_next(request)
	# Basic security headers
	response.headers.setdefault("X-Content-Type-Options", "nosniff")
	response.headers.setdefault("X-Frame-Options", "DENY")
	response.headers.setdefault("Referrer-Policy", "no-referrer")
	response.headers.setdefault("Permissions-Policy", "geolocation=()")
	# Content-Security-Policy should be tuned for your frontend
	response.headers.setdefault("Content-Security-Policy", "default-src 'self'")
	return response


app.include_router(router)

# Shared service instance (in-memory)
chat_service = ChatService()


# --- Exception handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	logger.debug("Validation error", exc_info=exc)
	payload = ChatError(code="validation_error", message="Request validation failed", details=exc.errors())
	return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload.model_dump())


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
	logger.exception("Unhandled exception during request")
	payload = ChatError(code="internal_error", message="Internal server error", details=str(exc))
	return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump())


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def post_chat(request: ChatRequest):
	"""Send a chat message and receive an assistant reply.

	If session_id is omitted, a new session will be created automatically.
	"""
	try:
		sid = request.session_id
		if not sid:
			sid = await chat_service.create_session()
		await chat_service.append_user_message(sid, request.message.text, meta=request.message.meta)
		resp = await chat_service.generate_reply(sid, provider_preference=request.provider)
		# map LLMResponse -> ChatResponse
		return ChatResponse(ok=resp.ok, provider=resp.provider, model=resp.model, text=resp.text, raw=resp.raw, error=resp.error)
	except KeyError:
		raise HTTPException(status_code=404, detail="session not found")
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(system_prompt: str | None = None):
	sid = await chat_service.create_session(system_prompt=system_prompt)
	return JSONResponse(status_code=201, content={"session_id": sid})


@router.get("/sessions")
async def list_sessions():
	items = await chat_service.list_sessions()
	return items


@router.get("/sessions/{session_id}/history", response_model=ConversationHistory)
async def get_history(session_id: str):
	try:
		session = await chat_service.get_session(session_id)
		if not session:
			raise HTTPException(status_code=404, detail="session not found")
		return ConversationHistory(session_id=session.id, system_prompt=session.system_prompt, messages=[m.__dict__ for m in session.history])
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
	try:
		await chat_service.clear_session(session_id)
		return JSONResponse(status_code=204, content={})
	except KeyError:
		raise HTTPException(status_code=404, detail="session not found")


@router.post("/sessions/{session_id}/export")
async def export_session(session_id: str):
	try:
		path = await chat_service.export_session(session_id)
		return {"exported_path": path}
	except KeyError:
		raise HTTPException(status_code=404, detail="session not found")
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
	return {"status": "ok"}


@router.get("/models")
async def models():
	# lightweight info for the frontend/UI
	return {"default_model": chat_service.settings.default_model, "max_tokens": chat_service.settings.max_response_tokens}

