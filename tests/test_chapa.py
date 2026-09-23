import asyncio
import numpy as np
import pytest
import sounddevice as sd
from unittest.mock import AsyncMock, MagicMock, patch

from chapa_core import Booting, Output, Shutdown


# ---------- Booting ----------
@pytest.mark.asyncio
async def test_booting_loading(monkeypatch):
    fake = MagicMock(sd_default_device=2)
    monkeypatch.setattr("chapa_core.Settings.from_json", MagicMock(return_value=fake))
    monkeypatch.setattr("chapa_core.sd.query_devices", MagicMock(return_value=[]))
    monkeypatch.setattr(sd.default, "device", None)

    b = Booting()
    s = await b.loading()
    assert s is fake
    assert sd.default.device == 2


@pytest.mark.asyncio
async def test_before_check_loops_until_ready():
    b = Booting()
    sound_engine_obj = MagicMock()
    sound_engine_obj.is_ready = AsyncMock(side_effect=[False, False, True])
    input_obj = MagicMock()
    input_obj.is_ready = AsyncMock(return_value=True)

    await b.before_check(MagicMock(), sound_engine_obj, input_obj)
    assert sound_engine_obj.is_ready.await_count == 3


@pytest.mark.asyncio
async def test_before_check_waits_for_input():
    b = Booting()
    sound_engine_obj = MagicMock()
    sound_engine_obj.is_ready = AsyncMock(return_value=True)
    input_obj = MagicMock()
    input_obj.is_ready = AsyncMock(side_effect=[False, True])

    await b.before_check(MagicMock(), sound_engine_obj, input_obj)
    assert input_obj.is_ready.await_count == 2


# ---------- Output ----------
@pytest.mark.asyncio
async def test_output_soundplay(monkeypatch):
    played = []
    monkeypatch.setattr("chapa_core.sd.play",
                        lambda data, rate: played.append((data, rate)))
    monkeypatch.setattr("chapa_core.sd.wait", lambda: None)

    q = asyncio.Queue()
    data = np.zeros(100, dtype=np.float32)
    await q.put((data, 24000))

    out = Output()
    task = asyncio.create_task(out.soundplay(q))
    for _ in range(50):
        if played:
            break
        await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert played and played[0][1] == 24000


# ---------- Shutdown ----------
def test_shutdown_mac(monkeypatch):
    calls = []
    monkeypatch.setattr("chapa_core.subprocess.run",
                        lambda *a, **k: calls.append(a))
    Shutdown().Mac_shutdown()
    assert len(calls) == 4
    assert calls[0][0][0] == "osascript"
    assert calls[2][0][0] == "killall"


def test_shutdown_windows(monkeypatch):
    calls = []
    def fake_run(*a, **k):
        calls.append(a)
    monkeypatch.setattr("chapa_core.subprocess.run", fake_run)
    Shutdown().Window_shutdown()
    assert len(calls) == 4
    for c in calls:
        assert c[0][0] == "taskkill"
