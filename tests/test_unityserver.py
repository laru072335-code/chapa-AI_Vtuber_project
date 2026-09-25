import asyncio
import numpy as np
import pytest
import msgpack
from unittest.mock import AsyncMock, MagicMock

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


# =====================================================================
# handler
# =====================================================================
class TestHandler:
    @pytest.mark.asyncio
    async def test_handler_adds_and_removes_connection(self):
        s = unityserver()
        ws = _fake_ws()

        # メッセージを 1 件流してから終了させる非同期イテレータ
        async def fake_iter(_ws):
            yield "hello"

        ws.__aiter__ = lambda self=ws: fake_iter(ws)

        await s.handler(ws)
        # finally で remove されている
        assert ws not in s.connected

    @pytest.mark.asyncio
    async def test_handler_pushes_message_to_responce_queue(self):
        q = asyncio.Queue()
        s = unityserver(responce_queue=q)
        ws = _fake_ws()

        async def fake_iter(_ws):
            yield "msg1"
            yield "msg2"

        ws.__aiter__ = lambda self=ws: fake_iter(ws)

        await s.handler(ws)
        assert await q.get() == "msg1"
        assert await q.get() == "msg2"

    @pytest.mark.asyncio
    async def test_handler_no_responce_queue_is_ok(self):
        """responce_queue が None でも受信ループは回る（保存はしない）"""
        s = unityserver()
        ws = _fake_ws()

        async def fake_iter(_ws):
            yield "x"

        ws.__aiter__ = lambda self=ws: fake_iter(ws)
        await s.handler(ws)  # 例外なく完了

    @pytest.mark.asyncio
    async def test_handler_swallows_exception_and_cleans_up(self):
        """イテレーション中に例外が出ても finally が呼ばれて切断される"""
        s = unityserver()
        ws = _fake_ws()

        async def fake_iter(_ws):
            yield "ok"
            raise RuntimeError("boom")

        ws.__aiter__ = lambda self=ws: fake_iter(ws)

        await s.handler(ws)  # 例外は内部で握られる
        assert ws not in s.connected

    @pytest.mark.asyncio
    async def test_handler_skips_none_message(self):
        q = asyncio.Queue()
        s = unityserver(responce_queue=q)
        ws = _fake_ws()

        async def fake_iter(_ws):
            yield None
            yield "real"

        ws.__aiter__ = lambda self=ws: fake_iter(ws)
        await s.handler(ws)

        # None は put されず、"real" だけ入る
        assert q.qsize() == 1
        assert await q.get() == "real"


# =====================================================================
# _send_data
# =====================================================================
class TestSendData:
    @pytest.mark.asyncio
    async def test_sends_to_all_connected(self):
        s = unityserver()
        ws1, ws2 = _fake_ws(), _fake_ws()
        s.connected = {ws1, ws2}

        await s._send_data(0, ["a", "b"])

        ws1.send.assert_awaited_once()
        ws2.send.assert_awaited_once()
        # 両方に同じバイナリが送られる
        assert ws1.send.await_args.args[0] == ws2.send.await_args.args[0]

    @pytest.mark.asyncio
    async def test_payload_format(self):
        s = unityserver()
        ws = _fake_ws()
        s.connected = {ws}

        await s._send_data(2, [0.1, 0.2])
        packed = ws.send.await_args.args[0]
        assert _unpack(packed) == [2, [0.1, 0.2]]

    @pytest.mark.asyncio
    async def test_no_connected_is_noop(self):
        s = unityserver()
        # 空集合 → gather() は空で即完了、例外なし
        await s._send_data(0, "anything")


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


# =====================================================================
# send_subtitle
# =====================================================================
class TestSendSubtitle:
    @pytest.mark.asyncio
    async def test_forwards_pair_with_header_1(self, monkeypatch):
        s = unityserver()
        captured = []

        async def fake_send(head, data):
            captured.append((head, data))

        monkeypatch.setattr(s, "_send_data", fake_send)

        prompt_q = asyncio.Queue()
        answer_q = asyncio.Queue()
        await prompt_q.put(Message("u", "質問", "public", 1))
        await answer_q.put(Message("assistant", "回答", "public", 1))

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
        rate, data_bytes = data
        assert rate == 24000
        assert isinstance(data_bytes, bytes)
        # 元の float32 配列に復元できる
        restored = np.frombuffer(data_bytes, dtype=np.float32)
        np.testing.assert_array_almost_equal(restored, samples)

    @pytest.mark.asyncio
    async def test_float64_input_is_cast_to_float32(self, monkeypatch):
        """入力が float64 でも float32 に変換される"""
        s = unityserver()
        captured = []

        async def fake_send(head, data):
            captured.append((head, data))

        monkeypatch.setattr(s, "_send_data", fake_send)

        q = asyncio.Queue()
        samples = np.array([0.1, 0.2], dtype=np.float64)  # float64
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
        # float64 → float32 変換の丸め誤差の範囲で一致
        assert restored.dtype == np.float32
        np.testing.assert_array_almost_equal(restored, samples.astype(np.float32), decimal=6)


# =====================================================================
# main
# =====================================================================
class TestMain:
    @pytest.mark.asyncio
    async def test_main_test_mode(monkeypatch):
        """test=True なら 10 秒で終わる代わりに sleep を無効化して確認"""
        s = unityserver()

        # websockets.serve をモック
        fake_server = MagicMock()
        fake_server.close = MagicMock()
        fake_server.wait_closed = AsyncMock()

        async def fake_serve(handler, host, port):
            # handler が self.handler に束縛されていることを軽く確認
            assert handler.__self__ is s
            assert host == "127.0.0.1"
            assert port == 8765
            return fake_server

        monkeypatch.setattr("unityserver.websockets.serve", fake_serve)

        # 10 秒待ちを回避
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

        monkeypatch.setattr("unityserver.websockets.serve", fake_serve)

        task = asyncio.create_task(s.main(test=False))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        fake_server.close.assert_called_once()
        fake_server.wait_closed.assert_awaited_once()
