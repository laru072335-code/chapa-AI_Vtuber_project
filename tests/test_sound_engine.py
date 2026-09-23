import asyncio
import io
import json
import numpy as np
import pytest
import soundfile as sf
from unittest.mock import AsyncMock, MagicMock

from sound_engine import SoundProvider, VOICEVOXProvider, AivisProvider, COEIROINKProvider


# ---------- ヘルパ ----------
def _wav_bytes(duration=0.5, rate=24000):
    samples = np.zeros(int(duration * rate), dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, samples, rate, format="WAV")
    return buf.getvalue()


def _query_resp(phrases):
    r = MagicMock()
    r.json = MagicMock(return_value={"accent_phrases": phrases})
    return r


# ---------- SoundProvider (ABC) ----------
def test_sound_provider_is_abstract():
    with pytest.raises(TypeError):
        SoundProvider()  # 抽象メソッド未実装のため


# ---------- VOICEVOXProvider ----------
@pytest.mark.asyncio
async def test_voicevox_generate_voice_basic():
    provider = VOICEVOXProvider()
    client = AsyncMock()

    query_resp = _query_resp([
        {
            "moras": [
                {"vowel": "a", "consonant_length": 0.05, "vowel_length": 0.10},
                {"vowel": "i", "consonant_length": 0.0,  "vowel_length": 0.15},
            ]
        }
    ])
    synth_resp = MagicMock(content=_wav_bytes())
    client.post = AsyncMock(side_effect=[query_resp, synth_resp])

    in_q, sound_out_q, viseme_out_q = (asyncio.Queue(), asyncio.Queue(), asyncio.Queue())
    await in_q.put("こんにちは")

    task = asyncio.create_task(
        provider.generate_voice(client, 1, in_q, sound_out_q, viseme_out_q)
    )
    data, rate = await asyncio.wait_for(sound_out_q.get(), timeout=2)
    visemes = await asyncio.wait_for(viseme_out_q.get(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert rate == 24000
    assert len(data) > 0
    assert [v[0] for v in visemes] == ["a", "i"]
    # 累計: 0.1 + 0.15 = 0.25, 次は 0.25+0.15 = 0.40
    assert visemes[0][1] == pytest.approx(0.25)
    assert visemes[1][1] == pytest.approx(0.40)


@pytest.mark.asyncio
async def test_voicevox_generate_voice_none_lengths():
    """consonant_length/vowel_length が None の場合 0.0 として扱われる"""
    provider = VOICEVOXProvider()
    client = AsyncMock()
    query_resp = _query_resp([
        {"moras": [{"vowel": "N", "consonant_length": None, "vowel_length": None}]}
    ])
    synth_resp = MagicMock(content=_wav_bytes())
    client.post = AsyncMock(side_effect=[query_resp, synth_resp])

    in_q, sound_out_q, viseme_out_q = (asyncio.Queue(), asyncio.Queue(), asyncio.Queue())
    await in_q.put("ん")
    task = asyncio.create_task(
        provider.generate_voice(client, 0, in_q, sound_out_q, viseme_out_q)
    )
    await asyncio.wait_for(sound_out_q.get(), timeout=2)
    visemes = await asyncio.wait_for(viseme_out_q.get(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert visemes[0][0] == "n"
    assert visemes[0][1] == pytest.approx(0.1)  # 加算なし


@pytest.mark.asyncio
async def test_voicevox_is_ready_success():
    provider = VOICEVOXProvider()
    client = AsyncMock()
    client.get = AsyncMock(return_value=MagicMock(status_code=200))
    assert await provider.is_ready(client) is True
    assert client.get.await_count == 1


@pytest.mark.asyncio
async def test_voicevox_is_ready_failure(monkeypatch):
    provider = VOICEVOXProvider()
    client = AsyncMock()
    client.get = AsyncMock(side_effect=Exception("refused"))
    # リトライ待ちを無効化
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    assert await provider.is_ready(client) is False


# ---------- AivisProvider ----------
@pytest.mark.asyncio
async def test_aivis_generate_voice_basic():
    provider = AivisProvider()
    client = AsyncMock()
    query_resp = _query_resp([])  # viseme は生成しない
    synth_resp = MagicMock(content=_wav_bytes())
    client.post = AsyncMock(side_effect=[query_resp, synth_resp])

    in_q, sound_out_q, viseme_out_q = (asyncio.Queue(), asyncio.Queue(), asyncio.Queue())
    await in_q.put("テスト")
    task = asyncio.create_task(
        provider.generate_voice(client, 0, in_q, sound_out_q, viseme_out_q)
    )
    data, rate = await asyncio.wait_for(sound_out_q.get(), timeout=2)
    visemes = await asyncio.wait_for(viseme_out_q.get(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert rate == 24000
    assert visemes == []


@pytest.mark.asyncio
async def test_aivis_is_ready_returns_none():
    """未実装（pass のみ）なので None を返す"""
    provider = AivisProvider()
    assert await provider.is_ready(AsyncMock()) is None


# ---------- COEIROINKProvider ----------
def test_coeiroink_is_ready_returns_none():
    import asyncio as _a
    provider = COEIROINKProvider()
    assert _a.get_event_loop().run_until_complete(
        provider.is_ready(AsyncMock())
    ) is None


@pytest.mark.asyncio
async def test_coeiroink_generate_voice_raises():
    provider = COEIROINKProvider()
    with pytest.raises(NotImplementedError):
        await provider.generate_voice(
            AsyncMock(), 0,
            asyncio.Queue(), asyncio.Queue(), asyncio.Queue()
        )
