"""One door to the AI provider.

Everything that talks to Gemini goes through LLMClient, so the provider can be
swapped by changing .env, and every call gets the same throttle, retries,
caching and logging. Tests use a fake client with the same two methods.
"""
import hashlib
import json
import threading
import time
from collections import deque
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from backend.app.core.cache import get_cache
from backend.app.core.config import settings

T = TypeVar("T", bound=BaseModel)

EMBED_CACHE_TTL = 30 * 24 * 3600   # the same text always gives the same vector, keep it 30 days
EMBED_BATCH = 100                  # texts per embedding request


class LLMError(Exception):
    """the ai couldn't answer (not configured, rate limited, timeout, bad output). callers fall back"""


class LLMClient:
    """what the rest of the app may ask an ai for"""

    model = "none"

    def generate_json(self, feature: str, prompt: str, schema: type[T]) -> T:
        raise NotImplementedError

    def embed(self, feature: str, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class DisabledClient(LLMClient):
    """used when there's no api key: every ai feature falls back to the non-ai path"""

    def generate_json(self, feature, prompt, schema):
        raise LLMError("AI is not configured.")

    def embed(self, feature, texts):
        raise LLMError("AI is not configured.")


class Throttle:
    """at most max_per_minute calls in any 60 seconds (sliding window). waits if needed"""

    def __init__(self, max_per_minute: int, max_wait: float = 15.0):
        self.max = max_per_minute
        self.max_wait = max_wait
        self.calls: deque[float] = deque()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self.lock:
                t = time.monotonic()
                while self.calls and t - self.calls[0] > 60:
                    self.calls.popleft()
                if len(self.calls) < self.max:
                    self.calls.append(t)
                    return
                wait = 60 - (t - self.calls[0])
            if wait > self.max_wait:
                # better to fall back now than keep the student waiting
                raise LLMError("AI is busy right now, please try again in a minute.")
            time.sleep(wait)


def log_call(feature: str, model: str, started: float, success: bool,
             input_tokens: int | None = None, output_tokens: int | None = None, error: str | None = None) -> None:
    """saves one llm_calls row in its own session, so it never mixes with the request's changes"""
    from backend.app.db.session import SessionLocal
    from backend.app.models import LLMCall
    try:
        with SessionLocal() as db:
            db.add(LLMCall(feature=feature, model=model, success=success, error=(error or "")[:300] or None,
                           input_tokens=input_tokens, output_tokens=output_tokens,
                           latency_ms=int((time.monotonic() - started) * 1000)))
            db.commit()
    except Exception as e:  # logging must never break the feature itself
        print(f"[AI] couldn't log the call: {type(e).__name__}")


class GeminiClient(LLMClient):
    RETRIES = 3

    def __init__(self, api_key: str, model: str, embedding_model: str, dim: int, max_rpm: int,
                 timeout_seconds: int, sdk_client=None, logger=log_call, embed_max_rpm: int | None = None):
        from google import genai
        from google.genai import types
        self.types = types
        self.client = sdk_client or genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=timeout_seconds * 1000))
        self.model = model
        self.embedding_model = embedding_model
        self.dim = dim
        # each model has its own google limit, so each gets its own throttle
        self.throttles = {model: Throttle(max_rpm), embedding_model: Throttle(embed_max_rpm or max_rpm)}
        self.log = logger

    def _call(self, feature: str, model: str, fn):
        """throttle + retry with exponential backoff on 429 / 5xx, and log every attempt"""
        from google.genai import errors
        for attempt in range(self.RETRIES):
            self.throttles[model].acquire()
            started = time.monotonic()
            try:
                response = fn()
                return response, started
            except errors.APIError as e:
                self.log(feature, model, started, False, error=f"{e.code}: {e}")
                retryable = e.code == 429 or (e.code or 0) >= 500
                if not retryable or attempt == self.RETRIES - 1:
                    raise LLMError(f"AI request failed ({e.code}).") from e
                time.sleep(2 ** attempt)          # 1 s, 2 s, then give up
            except Exception as e:                # timeout, network
                self.log(feature, model, started, False, error=type(e).__name__)
                if attempt == self.RETRIES - 1:
                    raise LLMError("AI request failed.") from e
                time.sleep(2 ** attempt)
        raise LLMError("AI request failed.")

    def generate_json(self, feature: str, prompt: str, schema: type[T]) -> T:
        config = self.types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema, temperature=0.2)
        response, started = self._call(feature, self.model, lambda: self.client.models.generate_content(
            model=self.model, contents=prompt, config=config))
        usage = getattr(response, "usage_metadata", None)
        tokens = dict(input_tokens=getattr(usage, "prompt_token_count", None),
                      output_tokens=getattr(usage, "candidates_token_count", None))
        try:
            result = schema.model_validate_json(response.text or "")
        except ValidationError as e:
            self.log(feature, self.model, started, False, error="invalid json from model", **tokens)
            raise LLMError("AI gave an answer in the wrong shape.") from e
        self.log(feature, self.model, started, True, **tokens)
        return result

    def embed(self, feature: str, texts: list[str]) -> list[list[float]]:
        """vectors for texts. cached by text, so the same text is never sent twice"""
        cache = get_cache()
        keys = [f"emb:{self.embedding_model}:{self.dim}:{hashlib.sha256(t.encode()).hexdigest()}" for t in texts]
        found: dict[int, list[float]] = {}
        for i, key in enumerate(keys):
            hit = cache.get(key)
            if hit:
                found[i] = json.loads(hit)
        missing = [i for i in range(len(texts)) if i not in found]

        for start in range(0, len(missing), EMBED_BATCH):
            batch = missing[start:start + EMBED_BATCH]
            config = self.types.EmbedContentConfig(output_dimensionality=self.dim)
            # each text as its own Content: gemini-embedding-2 joins a plain list of strings into ONE vector
            contents = [self.types.Content(parts=[self.types.Part(text=texts[i])]) for i in batch]
            response, started = self._call(feature, self.embedding_model, lambda: self.client.models.embed_content(
                model=self.embedding_model, contents=contents, config=config))
            if len(response.embeddings) != len(batch):
                self.log(feature, self.embedding_model, started, False, error="wrong number of vectors")
                raise LLMError("AI returned the wrong number of embeddings.")
            self.log(feature, self.embedding_model, started, True)
            for i, emb in zip(batch, response.embeddings):
                found[i] = list(emb.values)
                cache.set(keys[i], json.dumps(found[i]), EMBED_CACHE_TTL)
        return [found[i] for i in range(len(texts))]


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    """the shared client. no GEMINI_API_KEY -> DisabledClient (the app still works)"""
    global _client
    if _client is None:
        if settings.llm_provider == "gemini" and settings.gemini_api_key:
            _client = GeminiClient(settings.gemini_api_key, settings.llm_model, settings.embedding_model,
                                   settings.embedding_dim, settings.llm_max_rpm, settings.llm_timeout_seconds,
                                   embed_max_rpm=settings.embed_max_rpm)
        else:
            _client = DisabledClient()
    return _client
