"""
Outputs/unityserver.py のテスト

テスト方針:
- websockets は AsyncMock / MagicMock で完全に差し替え、実ソケットは使わない
- websocket の async イテレータは手作りの非同期ジェネレータで再現する
- _send_data は msgpack でデコードしてペイロードの形式まで検証する
- main() は test=True で sleep を短絡、test=False で cancel して finally を確認
"""
import asyncio

import msgpack
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock

# 実際に読み込まれるモジュール経由でパッチするため、モジュール自体も import
import Outputs.unityserver as unityserver_module
from Outputs.unityserver import unityserver
from type_list import Message


# =====================================================================
# ヘルパ
# =====================================================================
def _fake_ws():
    """websocket のモック（send が呼ばれた内容を記録）"""
    ws = MagicMock()
    ws.send = AsyncMock()
    return ws


def _set_async_iter(ws, items):
    """
    ws の __aiter__ を「items を順に yield する非同期イテレータ」に差し替える。
    例外を yield したい場合は items に Exception インスタンスを混ぜる。
    """
    async def _gen():
        for item in items:
            if isinstance(item, BaseException):
                raise item
            yield item

    ws.__aiter__ = lambda self=ws: _gen()


def _unpack(packed_bytes):
    return msgpack.unpackb(packed_bytes, raw=False, strict_map_key=False)


# =====================================================================
# __init__
# =====================================================================
class TestInit:
    def test_default_state(self):
        s = unityserver()
        assert s.connected == set()
        assert s.responce_queue is None

    def test_with_responce_queue(self):
        q = asyncio.Queue()
        s = unityserver(responce_queue=q)
        assert s.responce_queue is q

    def test_connected_is_independent_per_instance(self):
        a, b = unityserver(), unityserver()
        a.connected.add("x")
        assert b.connected == set()


# =====================================================================
# handler
# =====================================================================
class TestHandler:
    @pytest.mark.asyncio
    async def test_handler_adds_and_removes_connection(self):
        s = unityserver()
        ws = _fake_ws()
        _set_async_iter(ws, ["hello"])

        await s.handler(ws)
        # finally で remove されている
        assert ws not in s.connected

    @pytest.mark.asyncio
    async def test_handler_pushes_messages_to_responce_queue(self):
        q = asyncio.Queue()
        s = unityserver(responce_queue=q)
        ws = _fake_ws()
        _set_async_iter(ws, ["msg1", "msg2"])

        await s.handler(ws)

        assert await q.get() == "msg1"
        assert await q.get() == "msg2"
        assert q.empty()

    @pytest.mark.asyncio
    async def test_handler_without_responce_queue_is_noop(self):
        """responce_queue が None でも受信ループは回る（put はしない）"""
        s = unityserver()
        ws = _fake_ws()
        _set_async_iter(ws, ["x", "y"])

        await s.handler(ws)  # 例外なく完了
        assert s.responce_queue is None
        assert ws not in s.connected

    @pytest.mark.asyncio
    async def test_handler_skips_none_message(self):
        """None メッセージは put されない（print もされない）"""
        q = asyncio.Queue()
        s = unityserver(responce_queue=q)
        ws = _fake_ws()
        _set_async_iter(ws, [None, "real"])

        await s.handler(ws)

        assert q.qsize() == 1
        assert await q.get() == "real"

    @pytest.mark.asyncio
    async def test_handler_swallows_exception_and_cleans_up(self):
        """イテレーション中の例外は内部で握られ、finally で切断される"""
        s = unityserver()
        ws = _fake_ws()
        _set_async_iter(ws, ["ok", RuntimeError("boom")])

        await s.handler(ws)  # 例外は外に漏れない
        assert ws not in s.connected

    @pytest.mark.asyncio
    async def test_handler_does_not_put_after_exception(self):
        q = asyncio.Queue()
        s = unityserver(responce_queue=q)
        ws = _fake_ws()
        _set_async_iter(ws, ["ok", RuntimeError("boom")])

        await s.handler(ws)
        assert await q.get() == "ok"
        assert q.empty()


# =====================================================================
# _send_data
# =====================================================================
class TestSendData:
    @pytest.mark.asyncio
    async def test_payload_format_is_head_then_data(self):
        s = unityserver()
        ws = _fake_ws()
        s.connected = {ws}

        await s._send_data(2, [0.1, 0.2])
        packed = ws.send.await_args.args[0]
        assert _unpack(packed) == [2, [0.1, 0.2]]

    @pytest.mark.asyncio
    async def test_sends_to_all_connected(self):
        s = unityserver()
        ws1, ws2 = _fake_ws(), _fake_ws()
        s.connected = {ws1, ws2}

        await s._send_data(0, ["a", "b"])

        ws1.send.assert_awaited_once()
        ws2.send.assert_awaited_once()
        # 同一の binary が送られる
        assert ws1.send.await_args.args[0] == ws2.send.await_args.args[0]

    @pytest.mark.asyncio
    async def test_no_connected_is_noop(self):
        s = unityserver()
        await s._send_data(0, "anything")  # gather() 空で即完了

    @pytest.mark.asyncio
    async def test_string_data_roundtrips(self):
        s = unityserver()
        ws = _fake_ws()
        s.connected = {ws}
        await s._send_data(1, ["a", "b"])
        packed = ws.send.await_args.args[0]
        assert _unpack(packed) == [1, ["a", "b"]]

    @pytest.mark.asyncio
    async def test_bytes_data_roundtrips(self):
        s = unityserver()
        ws = _fake_ws()
        s.connected = {ws}
        raw = b"\x00\x01\x02"
        await s._send_data(3, [24000, raw])
        packed = ws.send.await_args.args[0]
        head, data = _unpack(packed)
        assert head == 3
        assert data[0] == 24000
        assert data[1] == raw


# =====================================================================
# send_viseme
# =====================================================================
class TestSendViseme:
    @pytest.mark.asyncio
    async def test_forwards_with_header_0(self, monkeypatch):
        s = unityserver()
        captured = []

        async def fake_send(head, data):
            captured.append((head, data))

        monkeypatch.setattr(s, "_send_data", fake_send)

        q = asyncio.Queue()
        viseme = [["a", 0.25], ["i", 0.40]]
        await q.put(viseme)

        task = asyncio.create_task(s.send_viseme(q))
        for _ in range(50):
            if captured:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert captured[0] == (0, viseme)

    @pytest.mark.asyncio
    async def test_multiple_items(self, monkeypatch):
        s = unityserver()
        captured = []

        async def fake_send(head, data):
            captured.append((head, data))

        monkeypatch.setattr(s, "_send_data", fake_send)

        q = asyncio.Queue()
        await q.put([["a", 0.1]])
        await q.put([["i", 0.2], ["u", 0.3]])

        task = asyncio.create_task(s.send_viseme(q))
        for _ in range(100):
            if len(captured) >= 2:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert captured[0][0] == 0
        assert captured[1] == (0, [["i", 0.2], ["u", 0.3]])


# =====================================================================
# send_subtitle
# =====================================================================
class TestSendSubtitle:
    @pytest.mark.asyncio
    async def test_forwards_pair_of_contents_with_header_1(self, monkeypatch):
        s = unityserver()
        captured = []

        async def fake_send(head, data):
            captured.append((head, data))

        monkeypatch.setattr(s, "_send_data", fake_send)

        prompt_q = asyncio.Queue()
        answer_q = asyncio.Queue()
        await prompt_q.put(Message(user_name="u", content="質問", type="text",
                                   location="public", stream_id=1))
        await answer_q.put(Message(user_name="assistant", content="回答", type="text",
                                   location="public", stream_id=1))

        task = asyncio.create_task(s.send_subtitle(prompt_q, answer_q))
        for _ in range(50):
            if captured:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        head, data = captured[0]
        assert head == 1
        assert data == ["質問", "回答"]

    @pytest.mark.asyncio
    async def test_waits_for_both_queues(self, monkeypatch):
        """answer_q に来るまで送信しない"""
        s = unityserver()
        captured = []

        async def fake_send(head, data):
            captured.append((head, data))

        monkeypatch.setattr(s, "_send_data", fake_send)

        prompt_q = asyncio.Queue()
        answer_q = asyncio.Queue()
        await prompt_q.put(Message(user_name="u", content="Q", type="text",
                                   location="public", stream_id=1))

        task = asyncio.create_task(s.send_subtitle(prompt_q, answer_q))
        await asyncio.sleep(0.05)
        # answer がまだ来ていないので送信されていない
        assert captured == []

        await answer_q.put(Message(user_name="assistant", content="A", type="text",
                                   location="public", stream_id=1))
        for _ in range(50):
            if captured:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert captured[0] == (1, ["Q", "A"])


# =====================================================================
# send_au
# =====================================================================
class TestSendAu:
    @pytest.mark.asyncio
    async def test_forwards_with_header_2(self, monkeypatch):
        s = unityserver()
        captured = []

        async def fake_send(head, data):
            captured.append((head, data))

        monkeypatch.setattr(s, "_send_data", fake_send)

        q = asyncio.Queue()
        au_vec = [50.0, 70.0, 90.0]
        await q.put(au_vec)

        task = asyncio.create_task(s.send_au(q))
        for _ in range(50):
            if captured:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert captured[0] == (2, au_vec)


# =====================================================================
# send_sound
# =====================================================================
class TestSendSound:
    @pytest.mark.asyncio
    async def test_forwards_with_header_3_and_bytes(self, monkeypatch):
        s = unityserver()
        captured = []

        async def fake_send(head, data):
            captured.append((head, data))

        monkeypatch.setattr(s, "_send_data", fake_send)

        q = asyncio.Queue()
        samples = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        await q.put((samples, 24000))

        task = asyncio.create_task(s.send_sound(q))
        for _ in range(50):
            if captured:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        head, data = captured[0]
        assert head == 3
        # ソースは [rate, data_bytes] のリストで送る
        rate, data_bytes = data
        assert rate == 24000
        assert isinstance(data_bytes, bytes)
        restored = np.frombuffer(data_bytes, dtype=np.float32)
        np.testing.assert_array_almost_equal(restored, samples)

    @pytest.mark.asyncio
    async def test_float64_input_is_cast_to_float32(self, monkeypatch):
        s = unityserver()
        captured = []

        async def fake_send(head, data):
            captured.append((head, data))

        monkeypatch.setattr(s, "_send_data", fake_send)

        q = asyncio.Queue()
        samples = np.array([0.1, 0.2], dtype=np.float64)  # float64 で渡す
        await q.put((samples, 16000))

        task = asyncio.create_task(s.send_sound(q))
        for _ in range(50):
            if captured:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        _, (rate, data_bytes) = captured[0]
        restored = np.frombuffer(data_bytes, dtype=np.float32)
        assert restored.dtype == np.float32
        np.testing.assert_array_almost_equal(
            restored, samples.astype(np.float32), decimal=6)


# =====================================================================
# main
# =====================================================================
class TestMain:
    @pytest.mark.asyncio
    async def test_main_test_mode(self, monkeypatch):
        s = unityserver()

        fake_server = MagicMock()
        fake_server.close = MagicMock()
        fake_server.wait_closed = AsyncMock()

        async def fake_serve(handler, host, port):
            assert handler.__self__ is s   # 束縛メソッドであること
            assert host == "127.0.0.1"
            assert port == 8765
            return fake_server

        monkeypatch.setattr(unityserver_module.websockets, "serve", fake_serve)

        # test=True の 10 秒 wait を短絡
        async def fast_sleep(_):
            return None
        monkeypatch.setattr(asyncio, "sleep", fast_sleep)

        await s.main(test=True)

        fake_server.close.assert_called_once()
        fake_server.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_main_cleans_up_on_cancel(self, monkeypatch):
        """test=False の Future を cancel して finally が走ることを確認"""
        s = unityserver()

        fake_server = MagicMock()
        fake_server.close = MagicMock()
        fake_server.wait_closed = AsyncMock()

        async def fake_serve(handler, host, port):
            return fake_server

        monkeypatch.setattr(unityserver_module.websockets, "serve", fake_serve)

        task = asyncio.create_task(s.main(test=False))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        fake_server.close.assert_called_once()
        fake_server.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_main_propagates_serve_error(self, monkeypatch):
        """serve の起動自体が失敗したら例外がそのまま伝播する"""
        s = unityserver()

        async def fake_serve(handler, host, port):
            raise OSError("port in use")

        monkeypatch.setattr(unityserver_module.websockets, "serve", fake_serve)

        with pytest.raises(OSError, match="port in use"):
            await s.main(test=True)