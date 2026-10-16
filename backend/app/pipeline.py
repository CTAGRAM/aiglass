"""The core loop: audio -> transcript -> memory -> action items -> orchestrator.

Stdlib only. This is the reusable heart of the whole product — it does not care whether the audio came
from a DIY XIAO, a Brilliant Labs Halo, or a typed message, nor whether the brain is Hermes or a mock.
"""
from __future__ import annotations

from dataclasses import asdict

from .actions import extract_action_items
from .memory.store import MemoryStore
from .orchestrator.base import Orchestrator
from .stt.base import STT
from .vision.base import VisionCaptioner


class Pipeline:
    def __init__(
        self,
        stt: STT,
        memory: MemoryStore,
        orchestrator: Orchestrator,
        vision: VisionCaptioner | None = None,
    ) -> None:
        self._stt = stt
        self._memory = memory
        self._orch = orchestrator
        self._vision = vision

    def process(self, audio: bytes, speaker: str | None = None) -> dict:
        transcript = self._stt.transcribe(audio)
        if not transcript:
            return {"transcript": "", "transcript_id": None, "actions": []}

        transcript_id = self._memory.add_transcript(transcript, speaker=speaker)

        results = []
        for item in extract_action_items(transcript):
            memory_id = self._memory.add_memory("action_item", item.text, source="pipeline")
            dispatch_result = self._orch.dispatch(item)
            results.append(
                {"action": asdict(item), "memory_id": memory_id, "dispatch": dispatch_result}
            )

        return {"transcript": transcript, "transcript_id": transcript_id, "actions": results}

    def process_frame(self, image: bytes) -> dict:
        """Caption a camera frame (Ray-Ban sends ~1 JPEG/sec) and store it as a searchable observation."""
        if self._vision is None:
            return {"caption": "", "memory_id": None}
        caption = self._vision.describe(image)
        if not caption:
            return {"caption": "", "memory_id": None}
        memory_id = self._memory.add_memory("observation", caption, source="camera")
        return {"caption": caption, "memory_id": memory_id}
