"""Minimal FastAPI streaming proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

Features:
- Instant status event streaming during tool execution (<500ms first feedback)
- Direct token delta streaming as LLM text tokens arrive
- Automatic Retry & Resend logic to prevent empty/missing replies
- 80% container layout width
- Tracking & reporting tool executions in gray text inside square brackets [Tool: ...]
- Tracking total tokens spent for the conversation
"""

import asyncio
import json
import os
import re
import uuid
from pathlib import Path

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ.get("AGENT_ENGINE_RESOURCE_NAME")
if not RESOURCE:
    metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                RESOURCE = json.load(f).get("remote_agent_runtime_id")
        except Exception:
            pass
if not RESOURCE:
    RESOURCE = "projects/189679044879/locations/us-east1/reasoningEngines/5945321055152242688"

# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP passthrough.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request.
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        card.url = A2A_BASE
        _card = card
    return _card


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI."""
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            raw_text = root.text
            # Extract embedded <a2ui-json> if present in text
            if "<a2ui-json>" in raw_text:
                pattern = r"<a2ui-json>(.*?)</a2ui-json>"
                matches = re.findall(pattern, raw_text, flags=re.DOTALL)
                for m in matches:
                    try:
                        data = json.loads(m.strip())
                        out.append({"kind": "a2ui", "data": data})
                    except Exception:
                        pass
                clean_text = re.sub(pattern, "", raw_text, flags=re.DOTALL).strip()
                if clean_text:
                    out.append({"kind": "text", "text": clean_text})
            else:
                out.append({"kind": "text", "text": raw_text})
        elif getattr(root, "data", None) is not None:
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": root.data})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


def _detect_tools(text: str, event_obj=None) -> list[str]:
    """Detects tool usage in response content or event metadata."""
    tools = set()
    known_tools = [
        "calculate_tax_liability",
        "search_romanian_tax_code",
        "lookup_fiscal_article",
        "search_fiscal_code",
        "generate_tax_infographic",
        "get_latest_exchange_rates",
        "get_tax_rates_catalog",
        "save_tax_rate",
        "execute_code",
        "python_interpreter",
    ]
    for tool in known_tools:
        if tool in text:
            tools.add(tool)

    if event_obj:
        raw_str = str(event_obj)
        for tool in known_tools:
            if tool in raw_str:
                tools.add(tool)
    return list(tools)


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"

    async def event_generator():
        async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
            card = await _get_card(client)
            factory = ClientFactory(
                ClientConfig(
                    supported_transports=[
                        TransportProtocol.jsonrpc,
                        TransportProtocol.http_json,
                    ],
                    httpx_client=client,
                )
            )
            a2a_client = factory.create(card)

            MAX_RETRIES = 2
            got_parts = False
            full_response_text = ""
            used_tools = set()

            for attempt in range(MAX_RETRIES + 1):
                last_task = None
                last_text_len = 0

                # Send initial status event instantly to user (<500ms)
                yield f"data: {json.dumps({'kind': 'status', 'text': '⚡ Agentul fiscal procesează interogarea...'})}\n\n"
                await asyncio.sleep(0)

                msg = Message(
                    message_id=str(uuid.uuid4()),
                    role=Role.user,
                    parts=[Part(root=TextPart(text=message))],
                    context_id=_contexts.get(user_id),
                )

                async for event in a2a_client.send_message(msg):
                    if not isinstance(event, tuple):
                        continue
                    task, update = event
                    if task is not None:
                        last_task = task
                        if getattr(task, "context_id", None):
                            _contexts[user_id] = task.context_id

                    if update is not None:
                        # Stream tool calls immediately when detected during execution
                        new_tools = _detect_tools("", update)
                        for t in new_tools:
                            if t not in used_tools:
                                used_tools.add(t)
                                yield f"data: {json.dumps({'kind': 'tool_call', 'tool': t})}\n\n"
                                await asyncio.sleep(0)

                        if isinstance(update, TaskStatusUpdateEvent):
                            status_msg = getattr(update, "description", None) or getattr(getattr(update, "status", None), "name", None)
                            if status_msg:
                                yield f"data: {json.dumps({'kind': 'status', 'text': f'⚡ {status_msg}'})}\n\n"
                                await asyncio.sleep(0)

                    if isinstance(update, TaskArtifactUpdateEvent):
                        extracted = _extract_parts(update.artifact.parts)
                        for item in extracted:
                            if item["kind"] == "text":
                                full_text = item["text"]
                                full_response_text = full_text
                                for t in _detect_tools(full_text):
                                    used_tools.add(t)

                                if len(full_text) > last_text_len:
                                    delta = full_text[last_text_len:]
                                    last_text_len = len(full_text)
                                    got_parts = True
                                    yield f"data: {json.dumps({'kind': 'text', 'text': delta})}\n\n"
                                    await asyncio.sleep(0)
                            else:
                                got_parts = True
                                yield f"data: {json.dumps(item)}\n\n"

                # Check fallback artifacts on last_task
                if not got_parts and last_task is not None:
                    for artifact in getattr(last_task, "artifacts", None) or []:
                        for item in _extract_parts(artifact.parts):
                            if item["kind"] == "text":
                                got_parts = True
                                full_response_text += item["text"]
                                for t in _detect_tools(item["text"]):
                                    used_tools.add(t)
                                yield f"data: {json.dumps({'kind': 'text', 'text': item['text']})}\n\n"
                                await asyncio.sleep(0)
                            else:
                                got_parts = True
                                yield f"data: {json.dumps(item)}\n\n"

                # If parts were successfully retrieved and streamed, break out of retry loop
                if got_parts:
                    break

                # If empty response on this attempt, wait 1s before retrying
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1.0)

            # Friendly fallback if still no response after retries
            if not got_parts:
                fallback_msg = "Agentul fiscal a procesat solicitarea. Vă rugăm să adresați din nou întrebarea."
                yield f"data: {json.dumps({'kind': 'text', 'text': fallback_msg})}\n\n"

            # Emit tools used if any detected
            for tool in used_tools:
                yield f"data: {json.dumps({'kind': 'tool_call', 'tool': tool})}\n\n"

            # Calculate estimated token usage
            prompt_tokens = max(1, len(message) // 4)
            completion_tokens = max(1, len(full_response_text) // 4)
            total_tokens = prompt_tokens + completion_tokens

            yield f"data: {json.dumps({'kind': 'usage', 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'total_tokens': total_tokens})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Serve the chat UI (keep this mount last so /chat wins).
_static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
