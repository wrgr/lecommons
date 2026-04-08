from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VertexConfig:
    project_id: str
    location: str
    model_name: str


class VertexGenerator:
    """Thin wrapper around Vertex Gemini text generation."""

    def __init__(self, config: VertexConfig):
        self.config = config
        self._model = None

    def _ensure_model(self):
        if self._model is not None:
            return self._model

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
        except Exception as exc:  # pragma: no cover - import behavior depends on runtime
            raise RuntimeError(
                "Vertex AI dependencies are not available. Install google-cloud-aiplatform."
            ) from exc

        vertexai.init(project=self.config.project_id, location=self.config.location)
        self._model = GenerativeModel(self.config.model_name)
        return self._model

    def generate(self, prompt: str, temperature: float = 0.1, max_output_tokens: int = 900) -> str:
        model = self._ensure_model()
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            },
        )
        text = getattr(response, "text", None)
        if text:
            return str(text).strip()

        # Compatibility fallback for SDK variants where text is under candidates.
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", None) or []
            for part in parts:
                value = getattr(part, "text", None)
                if value:
                    return str(value).strip()

        raise RuntimeError("Vertex model returned no text response.")


class LocalGroundedGenerator:
    """Fallback text generator for local development without Vertex access."""

    def generate(self, prompt: str, temperature: float = 0.0, max_output_tokens: int = 900) -> str:
        del temperature, max_output_tokens
        # Returns a compact deterministic output that keeps grounding requirements.
        marker = "CONTEXT_SNIPPETS_START"
        if marker not in prompt:
            return "INSUFFICIENT_GROUNDED_CONTEXT"
        snippets = prompt.split(marker, 1)[1]
        lines = [ln.strip() for ln in snippets.splitlines() if ln.strip()]
        evidence_lines = [ln for ln in lines if ln.startswith("[")][:3]
        if not evidence_lines:
            return "INSUFFICIENT_GROUNDED_CONTEXT"
        joined = " ".join(evidence_lines)
        return (
            "Grounded summary based on retrieved corpus evidence: "
            f"{joined}"
        )
