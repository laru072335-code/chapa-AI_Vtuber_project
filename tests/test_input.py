import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from Input import (
    Input_format, socialstream_input, Discord_input,
    Desktop_input, Stream_input,
)
from type_list import Message


# ---------- ABC ----------
def test_input_format_is_abstract():
    with pytest.raises(TypeError):
        Input_format(1, "public")


# ---------- socialstream ----------
@pytest.mark.asyncio
async def test_socialstream_get_comment(monkeypatch):
    obj = socialstream_input(1)
    obj.session_key = "KEY"

    messages = [json.dumps({"chatname": "u1", "chatmessage": "hello"}),
                json.dumps({"chatname": "u2", "chatmessage": "world"})]

    class FakeWS:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def recv(self):
            if messages:
                return messages.pop(0)
            await asyncio.sleep(10)

    monkeypatch.setattr("Input.websockets.connect",
                        lambda uri: FakeWS())

    q1, q2 = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(obj.latest_get_comment(q1, q2))
    m1 = await asyncio.wait_for(q1.get(), timeout=2)
    m2 = await asyncio.wait_for(q2.get(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert m1.content == "hello"
    assert m1.user_name == "u1"
    assert m1.location == "public"
    assert m1.stream_id == 1
    assert m2.content == "hello"  # 両方のキューに配る


@pytest.mark.asyncio
async def test_socialstream_is_ready_true(monkeypatch):
    obj = socialstream_input(1)
    obj.session_key = "KEY"

    class FakeWS:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False

    monkeypatch.setattr("Input.websockets.connect", lambda uri: FakeWS())
    assert await obj.is_ready() is True


@pytest.mark.asyncio
async def test_socialstream_is_ready_false(monkeypatch):
    obj = socialstream_input(1)
    obj.session_key = "KEY"

    def fail(uri):
        raise OSError("nope")

    monkeypatch.setattr("Input.websockets.connect", fail)
    assert await obj.is_ready() is False


# ---------- Discord / Desktop ----------
@pytest.mark.asyncio
async def test_discord_placeholders():
    obj = Discord_input()
    assert obj.location == "public"
    assert await obj.latest_get_comment() is None
    assert await obj.is_ready() is None


@pytest.mark.asyncio
async def test_desktop_placeholders():
    obj = Desktop_input()
    assert obj.location == "private"
    assert await obj.latest_get_comment() is None
    assert await obj.is_ready() is None


# ---------- Stream ----------
@pytest.mark.asyncio
async def test_stream_input_is_ready(monkeypatch):
    obj = Stream_input(10)
    fake_channel = MagicMock()
    fake_client = MagicMock()
    fake_client.channel = MagicMock(return_value=fake_channel)

    async def fake_create(url, key):
        return fake_client

    monkeypatch.setattr("Input.acreate_client", fake_create)
    monkeypatch.setenv("COMMENT_SUPABASE_URL", "http://x")
    monkeypatch.setenv("COMMENT_SUPABASE_KEY", "k")

    assert await obj.is_ready() is True
    assert obj.channel is fake_channel
