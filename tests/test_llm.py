"""LLM client: caching makes re-runs offline, accounting is measured, the key never leaks."""

from types import SimpleNamespace

import numpy as np
import pytest
from gw_common.llm import LLMClient, LLMSettings


class FakeOpenAI:
    def __init__(self):
        self.chat_calls = 0
        self.embed_calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))
        self.embeddings = SimpleNamespace(create=self._embed)

    def _chat(self, **kwargs):
        self.chat_calls += 1
        return SimpleNamespace(
            model=kwargs["model"],
            choices=[SimpleNamespace(message=SimpleNamespace(content="planning"))],
            usage=SimpleNamespace(prompt_tokens=12, completion_tokens=1),
        )

    def _embed(self, model, input):
        self.embed_calls += 1
        data = [SimpleNamespace(embedding=[float(len(t)), 1.0, 0.0]) for t in input]
        return SimpleNamespace(data=data, usage=SimpleNamespace(prompt_tokens=len(input)))


def _client(tmp_path, **overrides):
    settings = LLMSettings(api_key="sk-test", chat_model="test-chat", embed_model="test-embed", **overrides)
    fake = FakeOpenAI()
    return LLMClient(settings, cache_path=tmp_path / "llm.sqlite", client=fake), fake


def test_chat_is_cached_and_accounted(tmp_path):
    client, fake = _client(tmp_path)
    msgs = [{"role": "user", "content": "classify"}]
    first = client.chat(msgs)
    second = client.chat(msgs)
    assert first.text == second.text == "planning"
    assert (first.cached, second.cached) == (False, True)
    assert fake.chat_calls == 1
    assert client.usage == {"calls": 1, "cache_hits": 1, "input_tokens": 12, "output_tokens": 1}


def test_changing_temperature_is_a_different_request(tmp_path):
    client, fake = _client(tmp_path)
    msgs = [{"role": "user", "content": "classify"}]
    client.chat(msgs, temperature=0.0)
    client.chat(msgs, temperature=0.7)
    assert fake.chat_calls == 2


def test_embed_caches_per_text_and_normalises(tmp_path):
    client, fake = _client(tmp_path)
    a = client.embed(["solar panels", "water use"])
    b = client.embed(["water use", "carbon emissions"])
    assert fake.embed_calls == 2              # second call only sent the unseen text
    assert np.allclose(np.linalg.norm(a, axis=1), 1.0)
    assert np.allclose(a[1], b[0])


def test_missing_model_and_key_fail_loudly(tmp_path):
    client = LLMClient(LLMSettings(api_key=None, chat_model=None), cache_path=tmp_path / "c.sqlite")
    with pytest.raises(RuntimeError, match="GW_CHAT_MODEL"):
        client.chat([{"role": "user", "content": "x"}])
    client2 = LLMClient(LLMSettings(api_key=None, chat_model="m"), cache_path=tmp_path / "d.sqlite")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        client2.chat([{"role": "user", "content": "x"}])


def test_describe_never_contains_the_key(tmp_path):
    settings = LLMSettings(api_key="sk-secret-value", chat_model="m")
    assert "sk-secret-value" not in str(settings.describe())
