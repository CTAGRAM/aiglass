"""Local Whisper STT via faster-whisper. Optional — import only when actually used.

Install (once wheels exist for your Python): `pip install faster-whisper`
Expects 16 kHz mono 16-bit PCM bytes (what the firmware/app should send).
"""
from __future__ import annotations

import io
import wave


class WhisperSTT:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8") -> None:
        from faster_whisper import WhisperModel  # optional dep, imported lazily

        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio: bytes) -> str:
        # Wrap raw PCM in an in-memory WAV so faster-whisper can decode it.
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)  # 16-bit
            w.setframerate(16000)
            w.writeframes(audio)
        buf.seek(0)
        segments, _ = self._model.transcribe(buf, vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments).strip()
