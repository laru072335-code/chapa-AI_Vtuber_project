"""
chapa_core.py のテスト

- Output クラスは現状 chapa_core.py に存在しないためテスト対象から除外
- Shutdown は mac/windows いずれも subprocess.run を 3 回呼ぶ（VOICEVOX, virtual_roid, socialstream）
"""
import asyncio
import subprocess
import pytest
from unittest.mock import AsyncMock, MagicMock

from chapa_core import Booting, Shutdown


# =====================================================================
# Booting
# =====================================================================
class TestBooting:
    @pytest.mark.asyncio
    async def test_loading_returns_settings(self, monkeypatch):
        fake = MagicMock()
        monkeypatch.setattr(
            "chapa_core.Settings.from_json",
            MagicMock(return_value=fake),
        )
        s = await Booting().loading()
        assert s is fake

    @pytest.mark.asyncio
    async def test_loading_uses_setting_jsonc(self, monkeypatch):
        called_with = []

        def fake_from_json(path):
            called_with.append(path)
            return MagicMock()

        monkeypatch.setattr("chapa_core.Settings.from_json", fake_from_json)
        await Booting().loading()
        assert called_with == ["setting.jsonc"]

    @pytest.mark.asyncio
    async def test_before_check_waits_until_sound_ready(self):
        b = Booting()
        sound = MagicMock()
        sound.is_ready = AsyncMock(side_effect=[False, False, True])
        inputer = MagicMock()
        inputer.is_ready = AsyncMock(return_value=True)

        await b.before_check(MagicMock(), sound, inputer)
        assert sound.is_ready.await_count == 3

    @pytest.mark.asyncio
    async def test_before_check_waits_until_input_ready(self):
        b = Booting()
        sound = MagicMock()
        sound.is_ready = AsyncMock(return_value=True)
        inputer = MagicMock()
        inputer.is_ready = AsyncMock(side_effect=[False, True])

        await b.before_check(MagicMock(), sound, inputer)
        assert inputer.is_ready.await_count == 2

    @pytest.mark.asyncio
    async def test_before_check_short_circuits_input(self):
        """sound が False のときは and の短絡で input.is_ready は呼ばれない"""
        b = Booting()
        sound = MagicMock()
        sound.is_ready = AsyncMock(side_effect=[False, True])
        inputer = MagicMock()
        inputer.is_ready = AsyncMock(return_value=True)

        await b.before_check(MagicMock(), sound, inputer)
        assert sound.is_ready.await_count == 2
        assert inputer.is_ready.await_count == 1


# =====================================================================
# Shutdown
# =====================================================================
class TestShutdown:
    def test_mac_shutdown_runs_osascript_three_times(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "chapa_core.subprocess.run",
            lambda *a, **k: calls.append(a),
        )
        Shutdown().Mac_shutdown()

        assert len(calls) == 3
        for c in calls:
            assert c[0][0] == "osascript"
            assert c[0][1] == "-e"
        scripts = [c[0][2] for c in calls]
        assert any("VOICEVOX" in s for s in scripts)
        assert any("virtual_roid" in s for s in scripts)
        assert any("socialstream" in s for s in scripts)

    def test_windows_shutdown_runs_taskkill_three_times(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "chapa_core.subprocess.run",
            lambda *a, **k: calls.append(a),
        )
        Shutdown().Window_shutdown()

        assert len(calls) == 3
        for c in calls:
            assert c[0][0] == "taskkill"
            assert c[0][1] == "/F"
            assert c[0][2] == "/IM"

    def test_windows_shutdown_suppresses_stderr(self, monkeypatch):
        captured = {}

        def fake_run(*a, **k):
            captured["stderr"] = k.get("stderr")

        monkeypatch.setattr("chapa_core.subprocess.run", fake_run)
        Shutdown().Window_shutdown()
        assert captured["stderr"] is subprocess.DEVNULL