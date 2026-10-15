"""
Inputs.py のテスト

- モジュール名は Inputs（既存テストは Input と誤記していたので修正）
- Stream_input は (stream_id, public_key) の 2 引数を取る
"""
import asyncio
import json
import pytest
from unittest.mock import MagicMock

from Inputs import (
    Input_format, socialstream_input, Discord_input,
    Desktop_input, Stream_input,
)


# =====================================================================
# ABC
# =====================================================================
def test_input_format_is_abstract():
    with pytest.raises(TypeError):
        Input_format("public")


# =====================================================================
# socialstream_input
# =====================================================================
class TestSocialStream:
    @pytest.mark.asyncio
    async def test_latest_get_comment_distributes_to_all_queues(
            self, monkeypatch):
        obj = socialstream_input(stream_id=1)
        obj.session_key = "KEY"

        messages = [
            json.dumps({"chatname": "u1", "chatmessage": "hello"}),
            json.dumps({"chatname": "u2", "chatmessage": "world"}),
        ]

        class FakeWS:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def recv(self):
                if messages:
                    return messages.pop(0)
                await asyncio.sleep(10)

        monkeypatch.setattr("Inputs.websockets.connect", lambda uri: FakeWS())

        q1, q2 = asyncio.Queue(), asyncio.Queue()
        task = asyncio.create_task(obj.latest_get_comment(q1, q2))
        m1 = await asyncio.wait_for(q1.get(), timeout=2)
        m2 = await asyncio.wait_for(q2.get(), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # 両方のキューに同じメッセージ（1 件目）が届く
        assert m1.content == "hello"
        assert m1.user_name == "u1"
        assert m1.location == "public"
        assert m1.stream_id == 1
        assert m2.content == "hello"

    @pytest.mark.asyncio
    async def test_non_chat_message_is_ignored(self, monkeypatch):
        obj = socialstream_input(stream_id=1)
        obj.session_key = "KEY"

        messages = [
            json.dumps({"something": "else"}),
            json.dumps({"chatname": "u", "chatmessage": "hi"}),
        ]

        class FakeWS:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def recv(self):
                if messages:
                    return messages.pop(0)
                await asyncio.sleep(10)

        monkeypatch.setattr("Inputs.websockets.connect", lambda uri: FakeWS())

        q = asyncio.Queue()
        task = asyncio.create_task(obj.latest_get_comment(q))
        m = await asyncio.wait_for(q.get(), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert m.content == "hi"

    @pytest.mark.asyncio
    async def test_is_ready_true(self, monkeypatch):
        obj = socialstream_input(stream_id=1)
        obj.session_key = "KEY"

        class FakeWS:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False

        monkeypatch.setattr("Inputs.websockets.connect", lambda uri: FakeWS())
        assert await obj.is_ready() is True

    @pytest.mark.asyncio
    async def test_is_ready_false(self, monkeypatch):
        obj = socialstream_input(stream_id=1)
        obj.session_key = "KEY"

        def fail(uri):
            raise OSError("nope")

        monkeypatch.setattr("Inputs.websockets.connect", fail)
        assert await obj.is_ready() is False

    def test_location_is_public(self):
        assert socialstream_input(stream_id=1).location == "public"


# =====================================================================
# Discord / Desktop (未実装プレースホルダ)
# =====================================================================
class TestDiscordAndDesktop:
    @pytest.mark.asyncio
    async def test_discord_placeholders(self):
        obj = Discord_input()
        assert obj.location == "public"
        assert await obj.latest_get_comment() is None
        assert await obj.is_ready() is None

    @pytest.mark.asyncio
    async def test_desktop_placeholders(self):
        obj = Desktop_input()
        assert obj.location == "private"
        assert await obj.latest_get_comment() is None
        assert await obj.is_ready() is None


# =====================================================================
# Stream_input
# =====================================================================
class TestStreamInput:
    @pytest.mark.asyncio
    async def test_is_ready_creates_channel(self, monkeypatch):
        obj = Stream_input(stream_id=10, public_key="key")
        fake_channel = MagicMock()
        fake_client = MagicMock()
        fake_client.channel = MagicMock(return_value=fake_channel)

        async def fake_create(url, key):
            return fake_client

        monkeypatch.setattr("Inputs.acreate_client", fake_create)
        monkeypatch.setenv("COMMENT_SUPABASE_URL", "http://x")
        monkeypatch.setenv("COMMENT_SUPABASE_KEY", "k")

        assert await obj.is_ready() is True
        assert obj.channel is fake_channel

    def test_location_stream_id_jwt_key(self):
        obj = Stream_input(stream_id=5, public_key="k")
        assert obj.location == "public"
        assert obj.stream_id == 5
        assert obj.jwt_key == "k"