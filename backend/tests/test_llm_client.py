from types import SimpleNamespace

import pytest
from google.genai import errors
from pydantic import BaseModel

from backend.app.ai import llm_client
from backend.app.ai.llm_client import GeminiClient, LLMError, Throttle


class Answer(BaseModel):
    category: str


class FakeSDK:
    """looks like google-genai's client: .models.generate_content / .models.embed_content"""

    def __init__(self, generate_results=(), embed_dim=4, join_strings=False):
        self.join_strings = join_strings
        self.generate_results = list(generate_results)   # each: exception to raise, or response text
        self.embed_calls: list[list[str]] = []
        self.embed_dim = embed_dim
        self.models = self

    def generate_content(self, model, contents, config):
        result = self.generate_results.pop(0)
        if isinstance(result, Exception):
            raise result
        usage = SimpleNamespace(prompt_token_count=12, candidates_token_count=5)
        return SimpleNamespace(text=result, usage_metadata=usage)

    def embed_content(self, model, contents, config):
        texts = [c.parts[0].text for c in contents]      # one Content per text, like the real api needs
        self.embed_calls.append(texts)
        if self.join_strings:                            # what gemini-embedding-2 does with a plain list
            texts = texts[:1]
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[float(len(t))] * self.embed_dim) for t in texts])


def too_many():
    return errors.APIError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})


@pytest.fixture
def make(monkeypatch):
    monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)    # no real waiting in tests
    logs = []

    def build(sdk, rpm=100):
        client = GeminiClient("key", "model-x", "embed-x", 4, rpm, 5, sdk_client=sdk,
                              logger=lambda *a, **k: logs.append((a, k)))
        return client, logs
    return build


def test_retries_429_then_succeeds_and_logs_every_try(make):
    sdk = FakeSDK([too_many(), too_many(), '{"category": "Hostel"}'])
    client, logs = make(sdk)
    assert client.generate_json("triage", "p", Answer).category == "Hostel"
    successes = [a[3] for a, _ in logs]
    assert successes == [False, False, True]
    assert logs[-1][1] == {"input_tokens": 12, "output_tokens": 5}


def test_gives_up_after_three_429s(make):
    client, _ = make(FakeSDK([too_many(), too_many(), too_many()]))
    with pytest.raises(LLMError):
        client.generate_json("triage", "p", Answer)


def test_no_retry_on_a_bad_request(make):
    bad = errors.APIError(400, {"error": {"message": "bad", "status": "INVALID_ARGUMENT"}})
    sdk = FakeSDK([bad, '{"category": "x"}'])
    client, logs = make(sdk)
    with pytest.raises(LLMError):
        client.generate_json("triage", "p", Answer)
    assert len(logs) == 1          # 400 is our mistake, trying again won't help


def test_wrong_json_becomes_llm_error(make):
    client, logs = make(FakeSDK(['{"oops": 1}']))
    with pytest.raises(LLMError):
        client.generate_json("triage", "p", Answer)
    assert logs[-1][0][3] is False and "invalid json" in logs[-1][1]["error"]


def test_embeddings_are_cached(make):
    sdk = FakeSDK()
    client, _ = make(sdk)
    first = client.embed("embedding", ["fan broken", "wifi down"])
    again = client.embed("embedding", ["wifi down", "fan broken", "new text"])
    assert sdk.embed_calls == [["fan broken", "wifi down"], ["new text"]]   # only the new one was sent
    assert again[0] == first[1] and again[1] == first[0]


def test_throttle_refuses_long_waits():
    t = Throttle(max_per_minute=2, max_wait=1)
    t.acquire()
    t.acquire()
    with pytest.raises(LLMError):
        t.acquire()           # 3rd call in the same minute would wait ~60 s: fall back instead


def test_no_key_means_disabled(monkeypatch):
    from backend.app.core.config import settings
    monkeypatch.setattr(llm_client, "_client", None)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    assert isinstance(llm_client.get_llm(), llm_client.DisabledClient)
    monkeypatch.setattr(llm_client, "_client", None)


def test_wrong_number_of_vectors_is_an_error(make):
    client, logs = make(FakeSDK(join_strings=True))
    with pytest.raises(LLMError):
        client.embed("embedding", ["one", "two"])
    assert logs[-1][1]["error"] == "wrong number of vectors"


def test_text_and_embedding_calls_have_separate_limits(make):
    sdk = FakeSDK(['{"category": "a"}'])
    client, _ = make(sdk, rpm=1)          # only 1 text call per minute
    client.embed("embedding", ["x"])      # doesn't use up the text model's slot
    assert client.generate_json("triage", "p", Answer).category == "a"
