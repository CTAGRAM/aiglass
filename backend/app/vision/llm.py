"""Vision captioner backed by an OpenAI-compatible multimodal chat endpoint (OpenAI, Groq, or a local
server like llama.cpp/Ollama with a vision model). Stdlib only (urllib) — no SDK dependency.

Ray-Ban Meta streams ~1 JPEG/sec via the DAT SDK; each frame lands here, gets a one-line description,
and becomes a searchable "observation" memory the orchestrator can reason over.

Degrades gracefully: returns "" on any error so a flaky vision endpoint never breaks capture.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

_DEFAULT_PROMPT = "Describe what is in this image in one concise sentence. If text is visible, transcribe it."


class LLMVision:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 20.0,
        prompt: str = _DEFAULT_PROMPT,
    ) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._key = api_key
        self._model = model
        self._timeout = timeout
        self._prompt = prompt

    def describe(self, image: bytes) -> str:
        b64 = base64.b64encode(image).decode("ascii")
        payload = json.dumps(
            {
                "model": self._model,
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ],
                    }
                ],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError):
            return ""
