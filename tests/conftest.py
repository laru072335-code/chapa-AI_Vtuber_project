"""
共通フィクスチャと、プロジェクト固有モジュールのスタブ化。
- プロジェクトルートを sys.path に追加
- unityserver / 重量級依存（無い場合）を自動スタブ化
- type_list が無い場合のフォールバック
"""
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# --- プロジェクトルートを import 可能にする ---
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _can_import(name: str) -> bool:
    if name in sys.modules:
        return True
    try:
        __import__(name)
        return True
    except Exception:
        return False


def _stub_mock(name: str) -> None:
    if name in sys.modules:
        return
    m = MagicMock()
    m.__name__ = name
    sys.modules[name] = m


def _stub_plain(name: str, attrs: dict | None = None) -> None:
    if name in sys.modules:
        return
    m = types.ModuleType(name)
    for k, v in (attrs or {}).items():
        setattr(m, k, v)
    sys.modules[name] = m


# --- unityserver はプロジェクト固有なのでスタブ ---
if not _can_import("unityserver"):
    _stub_plain("unityserver", {"unityserver": MagicMock()})

# --- 重量級・任意依存はインポートできなければ MagicMock で代替 ---
for _name in ("sounddevice", "hdbscan", "supabase", "ollama",
              "onnxruntime", "tokenizers", "websockets"):
    if not _can_import(_name):
        _stub_mock(_name)


# --- type_list フォールバック ---
if not _can_import("type_list"):
    @dataclass
    class Message:
        user_name: str
        content: str
        location: str
        stream_id: int

    @dataclass
    class Settings:
        sd_default_device: int = 0
        DB_API: str = "http://test"
        input_type: str = "desktop"
        LLM_Tool: str = "ollama"
        ai_model: str = "test"
        setting_ai_text: str = "sys"
        soundEngine: str = "voicevox"
        soundEngine_path: str = "/tmp/voicevox"
        socialstream_path: str = "/tmp/socialstream"
        speaker: int = 1
        max_queue_size: int = 100
        sound_output: str = "Python"

        @classmethod
        def from_json(cls, path):
            return cls()

    _stub_plain("type_list", {"Message": Message, "Settings": Settings})


@pytest.fixture
def Message_factory():
    from type_list import Message
    return Message
