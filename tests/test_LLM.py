import asyncio
import json
import pytest
from unittest.mock import MagicMock

from LLM import LLMProvider, OllamaProvider, vLLMProvider
from type_list import Message


@pytest.fixture
def conversation_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = tmp_path / "conversation.json"
    p.write_text(json.dumps([{"role": "system", "content": "old"}]),
                 encoding="UTF-8")
    return p


# ---------- ABC ----------
def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()


# ---------- OllamaProvider ----------
def test_ollama_init_updates_system_prompt(conversation_file):
    provider = OllamaProvider("m1", "new-system")
    data = json.loads(conversation_file.read_text(encoding="UTF-8"))
    assert data[0]["content"] == "new-system"
    assert provider.AImodel == "m1"


def test_ollama_init_keeps_when_same(conversation_file):
    provider = OllamaProvider("m1", "old")
    data = json.loads(conversation_file.read_text(encoding="UTF-8"))
    assert data[0]["content"] == "old"


@pytest.mark.asyncio
async def test_ollama_create_comment(conversation_file, monkeypatch):
    provider = OllamaProvider("m", "sys")

    fake_response = {"message": {"content": "こんにちは。元気？"}}
    monkeypatch.setattr("LLM.ollama.chat", MagicMock(return_value=fake_response))

    in_q = asyncio.Queue()
    voice_q = asyncio.Queue()
    out_q = asyncio.Queue()
    await in_q.put(Message("user", "hi", "public", 1))

    task = asyncio.create_task(provider.create_comment(in_q, voice_q, out_q))
    msg = await asyncio.wait_for(out_q.get(), timeout=2)
    voice1 = await asyncio.wait_for(voice_q.get(), timeout=2)
    voice2 = await asyncio.wait_for(voice_q.get(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert msg.content == "こんにちは。元気？"
    assert msg.user_name == "assistant"
    assert msg.location == "public"
    assert msg.stream_id == 1
    # 句読点で分割される
    assert voice1 == "こんにちは。"
    assert voice2 == "元気？"


@pytest.mark.asyncio
async def test_ollama_create_comment_appends_history(conversation_file, monkeypatch):
    provider = OllamaProvider("m", "sys")
    monkeypatch.setattr(
        "LLM.ollama.chat",
        MagicMock(return_value={"message": {"content": "OK。"}})
    )

    in_q, voice_q, out_q = asyncio.Queue(), asyncio.Queue(), asyncio.Queue()
    await in_q.put(Message("user", "hello", "public", 1))

    task = asyncio.create_task(provider.create_comment(in_q, voice_q, out_q))
    await asyncio.wait_for(out_q.get(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    data = json.loads(conversation_file.read_text(encoding="UTF-8"))
    roles = [m["role"] for m in data]
    assert "user" in roles and "assistant" in roles


def test_ollama_create_summary_not_implemented(conversation_file):
    provider = OllamaProvider("m", "sys")
    with pytest.raises(NotImplementedError):
        provider.create_summary(["a", "b"])


# ---------- vLLMProvider ----------
def test_vllm_init_not_implemented():
    with pytest.raises(NotImplementedError):
        vLLMProvider()


def test_vllm_create_summary_not_implemented():
    with pytest.raises(NotImplementedError):
        vLLMProvider.__new__(vLLMProvider).create_summary(["a"])
