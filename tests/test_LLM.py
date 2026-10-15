"""
new_LLM.py のテスト

注意:
- 現行実装には OllamaProvider / vLLMProvider の完全な実装は無い。
  LLMProvider の __init__ は requests.get と conversation.json を触るため、
  フィクスチャで I/O をモックする。
- Get_content は内部で login → ブラウザ起動を伴うため必ずモックする。
"""
import asyncio
import json

import pytest
from unittest.mock import MagicMock

from new_LLM import LLMProvider, OllamaProvider
from type_list import Message


@pytest.fixture
def mocked_env(tmp_path, monkeypatch):
    """LLMProvider.__init__ が行う I/O をモックした環境を用意"""
    monkeypatch.chdir(tmp_path)

    conv = tmp_path / "conversation.json"
    conv.write_text(
        json.dumps([{"role": "system", "content": {"text": "old"}}]),
        encoding="UTF-8",
    )

    fake_resp = MagicMock()
    fake_resp.json.return_value = {"prompt": "from-api"}
    monkeypatch.setattr(
        "new_LLM.requests.get", MagicMock(return_value=fake_resp))
    # Get_content は login() を呼ぶためモック
    monkeypatch.setattr("new_LLM.Get_content", MagicMock())

    return conv


# =====================================================================
# __init__
# =====================================================================
class TestInit:
    def test_init_stores_model(self, mocked_env):
        p = LLMProvider("m1", "sys", "http://api", "http://web")
        assert p.AImodel == "m1"

    def test_init_updates_system_prompt_when_different(self, mocked_env):
        LLMProvider("m1", "new-system", "http://api", "http://web")
        data = json.loads(mocked_env.read_text(encoding="UTF-8"))
        assert data[0]["content"]["text"] == "new-system"

    def test_init_keeps_when_same(self, mocked_env):
        LLMProvider("m1", "old", "http://api", "http://web")
        data = json.loads(mocked_env.read_text(encoding="UTF-8"))
        assert data[0]["content"]["text"] == "old"

    def test_init_creates_get_content(self, mocked_env, monkeypatch):
        gc_cls = MagicMock()
        monkeypatch.setattr("new_LLM.Get_content", gc_cls)
        LLMProvider("m1", "s", "http://api", "http://web")
        gc_cls.assert_called_once_with("http://api", "http://web")

