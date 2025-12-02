import json
import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

_DEFAULT_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")


def call_llama(
    prompt: str,
    system_prompt: str,
    *,
    model: Optional[str] = None,
    format_hint: str = "json",
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """Call the local Ollama service and return a JSON-decoded response."""
    host = _DEFAULT_HOST.rstrip("/")
    # docker-compose.yml version doesn't specify model name, so we use the environment variable MATCH_MODEL_NAME or OLLAMA_MODEL, default to "llama3"
    selected_model = model or os.getenv("MATCH_MODEL_NAME") or os.getenv("OLLAMA_MODEL", "llama3")
    request_timeout = timeout or int(os.getenv("OLLAMA_TIMEOUT", "60"))

    payload: Dict[str, Any] = {
        "model": selected_model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    # Ollama supports format="json" to force the model to output JSON.
    if format_hint:
        payload["format"] = format_hint

    url_chat = f"{host}/api/chat"
    logger.debug("Calling Ollama at %s with model=%s", url_chat, selected_model)

    try:
        response = requests.post(url_chat, json=payload, timeout=request_timeout)
    except requests.RequestException as exc:
        logger.error("Call Ollama failed: %s", exc, exc_info=True)
        raise

    if response.status_code == 404:
        logger.warning("chat endpoint not available, fallback to /api/generate")
        return _call_generate(
            host=host,
            model=selected_model,
            prompt=_build_generate_prompt(system_prompt, prompt),
            timeout=request_timeout,
        )

    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Call Ollama failed: %s", exc, exc_info=True)
        raise

    return _parse_json_response(response.json())


def _call_generate(host: str, model: str, prompt: str, timeout: int) -> Dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    url_generate = f"{host}/api/generate"
    logger.debug("Calling Ollama fallback at %s with model=%s", url_generate, model)

    try:
        response = requests.post(url_generate, json=payload, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Call Ollama generate failed: %s", exc, exc_info=True)
        raise

    return _parse_json_response(response.json())


def _build_generate_prompt(system_prompt: str, user_prompt: str) -> str:
    return f"{system_prompt}\n\n{user_prompt}"


def _parse_json_response(data: Dict[str, Any]) -> Dict[str, Any]:
    if "message" in data:
        content = data.get("message", {}).get("content", "").strip()
    else:
        content = data.get("response", "").strip()

    if not content:
        logger.error("Ollama returned empty content: %s", data)
        raise ValueError("Ollama returned empty content")

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        logger.error("Parse Ollama JSON failed: %s", content)
        raise ValueError("Ollama returned content is not valid JSON") from exc


