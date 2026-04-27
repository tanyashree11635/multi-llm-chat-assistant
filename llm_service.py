"""Flexible LLM service supporting OpenAI and Google Gemini.

This module p    async def _complete_openai(self, messages: List[Dict[str, str]], max_tokens: int) -> LLMResponse:
        if not self.settings.openai_api_key:
            return LLMResponse(ok=False, provider="openai", model=self.settings.openai_model, error="Missing OPENAI_API_KEY")
        
        model = self.settings.openai_model
        # Try to use openai package if installed for better compatibilitydes an async-friendly LLMService that can call either OpenAI
or Gemini endpoints (via HTTP). It standardizes responses, enforces timeouts,
and logs errors. The implementation prefers using the `openai` package when
available for OpenAI; otherwise it falls back to httpx-based calls.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable, List

import httpx

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Rate limiting configuration
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2  # seconds
MAX_RETRY_DELAY = 32  # seconds
RATE_LIMIT_CODES = {429, 503}  # Status codes that indicate rate limiting

class RateLimiter:
    def __init__(self, requests_per_minute: int = 20):
        self.requests_per_minute = requests_per_minute
        self.interval = 60.0 / requests_per_minute
        self.last_request = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.time()
            time_since_last = now - self.last_request
            if time_since_last < self.interval:
                delay = self.interval - time_since_last
                await asyncio.sleep(delay)
            self.last_request = time.time()

async def with_retries(func: Callable, *args, **kwargs) -> Any:
    """Execute a function with exponential backoff retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:  # Last attempt
                raise  # Re-raise the last error
            
            error_str = str(e).lower()
            status_code = None
            
            # Try to extract status code from various error formats
            if "429" in error_str or "too many requests" in error_str:
                status_code = 429
            elif "503" in error_str or "service unavailable" in error_str:
                status_code = 503
                
            if status_code not in RATE_LIMIT_CODES:
                raise  # Not a rate limit error, re-raise immediately
            
            # Calculate delay with jitter
            delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_DELAY)
            logger.warning(f"Rate limit hit, retrying in {delay:.2f} seconds (attempt {attempt + 1}/{MAX_RETRIES})")
            await asyncio.sleep(delay)


@dataclass
class LLMResponse:
    ok: bool
    provider: str
    model: str
    text: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class LLMService:
    """Service to talk to LLM providers (OpenAI, Gemini).

    Example:
        settings = get_settings()
        svc = LLMService(settings=settings)
        resp = await svc.complete("Hello")
    """

    def __init__(self, settings=None, timeout: float = 30.0):
        self.settings = settings or get_settings()
        self.timeout = timeout
        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    async def close(self) -> None:
        await self._http_client.aclose()

    async def complete(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        provider: Optional[str] = None,  # 'openai' | 'gemini' | None
    ) -> LLMResponse:
        provider = provider or self.settings.default_provider
        max_tokens = max_tokens or self.settings.max_response_tokens

        if provider == "openai":
            return await self._complete_openai(messages, max_tokens=max_tokens)
        elif provider == "gemini":
            # Convert messages to a single prompt for Gemini
            prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)
            return await self._complete_gemini(prompt, max_tokens=max_tokens)
        else:
            return LLMResponse(ok=False, provider="none", model="", error="No provider available")

    def _choose_provider(self, preference: Optional[str]) -> str:
        pref = (preference or "").lower()
        if pref == "openai" and self.settings.openai_api_key:
            return "openai"
        if pref == "gemini" and self.settings.gemini_api_key:
            return "gemini"
        # fallback: prefer OpenAI if available, otherwise Gemini
        if self.settings.openai_api_key:
            return "openai"
        if self.settings.gemini_api_key:
            return "gemini"
        return ""

    async def _complete_openai(self, messages: List[Dict[str, str]], max_tokens: int) -> LLMResponse:
        # Input validation
        if not self.settings.openai_api_key:
            return LLMResponse(
                ok=False,
                provider="openai",
                model=self.settings.openai_model,
                error="Missing OPENAI_API_KEY"
            )

        # Validate and normalize message format
        valid_messages = []
        for msg in messages:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                logger.warning(f"Skipping invalid message format: {msg}")
                continue
            if msg['role'] not in ['system', 'user', 'assistant']:
                logger.warning(f"Converting invalid role {msg['role']} to user")
                msg['role'] = 'user'
            valid_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

        if not valid_messages:
            return LLMResponse(
                ok=False,
                provider="openai",
                model=self.settings.openai_model,
                error="No valid messages to send"
            )

        # Fixed model from settings
        model = self.settings.openai_model
        loop = asyncio.get_running_loop()

        # Try newer OpenAI client (v1+) first
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.settings.openai_api_key)
            
            def _sync_call(msg_list):
                logger.debug(f"OpenAI request - Model: {model}, Messages: {msg_list}")
                # Ensure all messages have role and content fields
                if not msg_list or not all(isinstance(m, dict) and 'role' in m and 'content' in m for m in msg_list):
                    raise ValueError(f"Invalid message format. Each message must have 'role' and 'content'. Got: {msg_list}")

                # Normalize roles
                valid_messages = []
                for msg in msg_list:
                    role = msg['role']
                    if role not in ['system', 'user', 'assistant']:
                        logger.warning(f"Converting invalid role '{role}' to 'user'")
                        role = 'user'
                    valid_messages.append({
                        'role': role,
                        'content': msg['content']
                    })

                logger.debug(f"Sending messages to OpenAI: {valid_messages}")
                return client.chat.completions.create(
                    model=model,
                    messages=valid_messages,
                    max_tokens=max_tokens
                )

            logger.debug("Using OpenAI v1+ client", extra={"provider": "openai", "model": model})
            try:
                resp = await loop.run_in_executor(None, lambda: _sync_call(messages))
                text = resp.choices[0].message.content if resp.choices else str(resp)
                return LLMResponse(ok=True, provider="openai", model=model, text=text, raw=resp)
            except Exception as e:
                logger.error(f"OpenAI API error: {str(e)}")
                return LLMResponse(ok=False, provider="openai", model=model, error=str(e))
            
        except Exception as e:
            # Fall back to direct API call if client fails
            logger.debug("OpenAI client failed, using HTTP API", extra={"error": str(e)})
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # Validate messages again for direct API call
            valid_messages = []
            for msg in messages:
                if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                    continue
                role = msg['role']
                if role not in ['system', 'user', 'assistant']:
                    role = 'user'
                valid_messages.append({
                    'role': role,
                    'content': msg['content']
                })
                
            if not valid_messages:
                return LLMResponse(ok=False, provider="openai", model=model, error="No valid messages to send")
                
            payload = {
                "model": model,
                "messages": valid_messages,
                "max_tokens": max_tokens
            }

            try:
                # Add exponential backoff retry for rate limits
                max_retries = 3
                retry_delay = 1  # Initial delay in seconds
                
                for attempt in range(max_retries):
                    try:
                        r = await self._http_client.post(url, json=payload, headers=headers)
                        r.raise_for_status()
                        data = r.json()
                        text = data["choices"][0]["message"]["content"]
                        return LLMResponse(ok=True, provider="openai", model=model, text=text, raw=data)
                    except Exception as retry_e:
                        if "429" in str(retry_e) and attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                            continue
                        raise  # Re-raise if it's not a rate limit or last attempt
                
                # If we get here, all retries failed
                if self.settings.gemini_api_key:
                    logger.warning("OpenAI requests failed. Falling back to Gemini.")
                    prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)
                    return await self._complete_gemini(prompt, max_tokens=max_tokens)
                return LLMResponse(ok=False, provider="openai", model=model, error="Max retries exceeded")
            except Exception as e:
                return LLMResponse(ok=False, provider="openai", model=model, error=str(e))

    async def _complete_gemini(self, prompt: str, max_tokens: int) -> LLMResponse:
        # Input validation
        if not self.settings.gemini_api_key:
            return LLMResponse(
                ok=False,
                provider="gemini", 
                model=self.settings.gemini_model,
                error="Missing GEMINI_API_KEY"
            )

        # Fixed model from settings
        model_name = self.settings.gemini_model

        try:
            # Use Gemini's REST API directly for better control
            # Try multiple model versions (current Gemini 2.5 models as of 2025)
            model_variants = [
                'gemini-2.5-flash-lite',                    # Lightest and fastest
                'gemini-2.5-flash-lite-preview-09-2025',   # Latest flash lite preview
                'gemini-2.5-pro',                           # Most powerful
                'gemini-2.5-pro-preview-tts',              # Pro with TTS
                'gemini-1.5-flash',                         # Fallback to older version
                'gemini-pro',                               # Legacy fallback
            ]
            
            last_error = None
            for model_variant in model_variants:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_variant}:generateContent?key={self.settings.gemini_api_key}"
                    headers = {"Content-Type": "application/json"}
                    
                    payload = {
                        "contents": [{"parts":[{"text": prompt}]}],
                        "generationConfig": {"maxOutputTokens": max_tokens}
                    }

                    logger.debug(f"Trying Gemini model: {model_variant}")
                    r = await self._http_client.post(url, json=payload, headers=headers)
                    r.raise_for_status()
                    data = r.json()

                    # Extract text from Gemini response
                    text = None
                    try:
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                    except (KeyError, IndexError):
                        text = str(data.get("text", data))

                    logger.info(f"Successfully used Gemini model: {model_variant}")
                    return LLMResponse(ok=True, provider="gemini", model=model_variant, text=text, raw=data)
                    
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    logger.warning(f"Model {model_variant} failed with error: {error_str}")
                    
                    # If it's an HTTP error, try to get more details
                    if hasattr(e, 'response'):
                        try:
                            error_detail = e.response.json() if hasattr(e.response, 'json') else e.response.text
                            logger.error(f"Gemini API response: {error_detail}")
                        except:
                            pass
                    continue
            
            # If all models failed, raise the last error
            if last_error:
                logger.error(f"All Gemini model variants failed. Last error: {str(last_error)}")
                raise last_error

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini error details: {error_msg}")
            
            # Check for specific error types
            if "403" in error_msg:
                msg = f"Invalid or expired Gemini API key. Error: {error_msg}"
            elif "404" in error_msg:
                msg = f"Gemini models not accessible. Error: {error_msg}"
            elif "400" in error_msg:
                msg = f"Bad request to Gemini API. Error: {error_msg}"
            else:
                msg = f"Gemini API error: {error_msg}"

            return LLMResponse(ok=False, provider="gemini", model=model_name, error=msg)

    async def _handle_openai_error(self, exc: Exception, prompt: str, model: str, max_tokens: int) -> LLMResponse:
        """Centralize OpenAI error handling.

        If the error indicates quota exhaustion (429 or 'insufficient_quota'), and a Gemini
        API key is configured, attempt to fallback to Gemini. Otherwise return a helpful
        error LLMResponse with guidance.
        """
        try:
            # Inspect httpx errors for status codes
            if isinstance(exc, httpx.HTTPStatusError) or isinstance(exc, httpx.HTTPError):
                # httpx.HTTPStatusError may have response attached
                resp = getattr(exc, "response", None)
                status = getattr(resp, "status_code", None) if resp is not None else None
                body = None
                try:
                    body = resp.json() if resp is not None else None
                except Exception:
                    body = getattr(resp, "text", None) if resp is not None else None

                if status == 429 or (isinstance(body, dict) and body.get("error", {}).get("code") in ("insufficient_quota",)):
                    logger.warning("OpenAI quota/exhausted detected (status=%s). Attempting Gemini fallback if available.", status)
                    if self.settings.gemini_api_key:
                        return await self._complete_gemini(prompt, model=model, max_tokens=max_tokens)
                    return LLMResponse(ok=False, provider="openai", model=model, error=f"OpenAI quota exceeded (status={status}). {body}")

            # Generic string inspection for legacy openai exceptions
            s = str(exc).lower()
            if "insufficient_quota" in s or "quota" in s or "429" in s:
                logger.warning("OpenAI quota-like error detected from exception message. Trying Gemini fallback if configured.")
                if self.settings.gemini_api_key:
                    return await self._complete_gemini(prompt, model=model, max_tokens=max_tokens)
                return LLMResponse(ok=False, provider="openai", model=model, error=f"OpenAI quota or rate limit error: {str(exc)}")

        except Exception:
            logger.exception("Error while handling OpenAI error")

        # Default: return the original error message
        return LLMResponse(ok=False, provider="openai", model=model, error=str(exc))


__all__ = ["LLMService", "LLMResponse"]
