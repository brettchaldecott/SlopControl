"""FastAPI gateway exposing an OpenAI-compatible ``/v1/chat/completions`` endpoint."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .config import GatewayConfig
from .fallback import create_fallback_chain, FallbackChain

logger = logging.getLogger(__name__)

# Shared mutable state (injected via lifespan)
_state: dict[str, Any] = {}


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: load config and build the fallback chain."""
    cfg = GatewayConfig.from_env()
    chain = create_fallback_chain(cfg, temperature=0)
    _state["config"] = cfg
    _state["chain"] = chain
    logger.info("PlanForge gateway started on %s", cfg.gateway_url)
    yield
    _state.clear()


def create_gateway_app() -> FastAPI:
    """Factory that returns the configured FastAPI application."""
    app = FastAPI(
        title="PlanForge LLM Gateway",
        version="0.2.0",
        lifespan=_lifespan,
    )

    @app.get("/healthz")
    async def healthz() -> dict:
        """Health check used by process managers."""
        return {"status": "ok", "gateway": "planforge"}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> dict:
        """OpenAI-compatible chat completions endpoint.

        The gateway ignores the ``model`` field in the request body
        (or uses it as a hint) and routes through the configured
        fallback chain instead.
        """
        try:
            body = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}")

        chain: FallbackChain = _state["chain"]
        messages_raw: list[dict[str, Any]] = body.get("messages", [])
        stream: bool = body.get("stream", False)

        # Convert raw dicts → LangChain message objects
        messages: list[Any] = []
        for msg in messages_raw:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                messages.append(SystemMessage(content=content))
            elif role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        try:
            if stream:
                return await _stream_response(chain, messages)
            else:
                return await _sync_response(chain, messages)
        except RuntimeError as exc:
            logger.error("All providers failed: %s", exc)
            raise HTTPException(status_code=503, detail=str(exc))

    return app


async def _sync_response(chain: FallbackChain, messages: list[Any]) -> dict:
    """Return a non-streaming OpenAI-compatible response."""
    result = await chain.ainvoke(messages)
    content_str = result.content if isinstance(result.content, str) else str(result.content)

    return {
        "id": "planforge-sync-0",
        "object": "chat.completion",
        "created": 0,
        "model": "gateway",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content_str,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


async def _stream_response(chain: FallbackChain, messages: list[Any]) -> StreamingResponse:
    """Return a streaming SSE response."""
    result = await chain.ainvoke(messages)
    content_str = result.content if isinstance(result.content, str) else str(result.content)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Simple single-chunk stream for now
        yield f"data: {json.dumps({'id':'planforge-stream-0','object':'chat.completion.chunk','model':'gateway','choices':[{'index':0,'delta':{'role':'assistant'},'finish_reason':None}]})}\n\n"
        yield f"data: {json.dumps({'id':'planforge-stream-0','object':'chat.completion.chunk','model':'gateway','choices':[{'index':0,'delta':{'content':content_str},'finish_reason':None}]})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
