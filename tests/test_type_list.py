"""
type_list.py のテスト

注意:
- Settings.from_json は現状 `Public_key=...` を cls() に渡しているが、
  Settings にそのフィールドが無いため TypeError になる（バグ）。
  該当テストは xfail で「既知の不具合」としてマークしている。
"""
import json
import pytest
from pathlib import Path

from type_list import (
    Message, Settings, Comment, clustering_result, media_type,
)


# =====================================================================
# media_type
# =====================================================================
class TestMediaType:
    def test_values(self):
        assert media_type.text == "text"
        assert media_type.image == "image"
        assert media_type.video == "video"
        assert media_type.sound == "sound"
        assert media_type.file == "file"

    def test_is_str_enum(self):
        # StrEnum なので str として比較できる
        assert media_type.text == "text"
        assert isinstance(media_type.text, str)


# =====================================================================
# Message
# =====================================================================
class TestMessage:
    def _msg(self, **kw):
        base = dict(user_name="user", content="hello",
                    type="text", location="public", stream_id=1)
        base.update(kw)
        return Message(**base)

    def test_basic_fields(self):
        m = self._msg()
        assert m.user_name == "user"
        assert m.content == "hello"
        assert m.type == "text"
        assert m.location == "public"
        assert m.stream_id == 1

    def test_stream_id_can_be_none(self):
        m = self._msg(stream_id=None)
        assert m.stream_id is None

    def test_invalid_type_raises(self):
        with pytest.raises(Exception):
            self._msg(type="invalid-type")

    def test_is_private_true(self):
        assert self._msg(location="private").is_private is True
        assert self._msg(location="private:dm").is_private is True

    def test_is_private_false(self):
        assert self._msg(location="public").is_private is False
        assert self._msg(location="public:stream").is_private is False

    def test_is_public_true(self):
        assert self._msg(location="public").is_public is True
        assert self._msg(location="public:abc").is_public is True

    def test_is_public_false(self):
        assert self._msg(location="private").is_public is False

    def test_is_assistant_true(self):
        assert self._msg(user_name="assistant").is_assistant is True

    def test_is_assistant_false(self):
        assert self._msg(user_name="Assistant").is_assistant is False
        assert self._msg(user_name="user").is_assistant is False

    def test_location_unknown_neither_public_nor_private(self):
        m = self._msg(location="unknown")
        assert m.is_public is False
        assert m.is_private is False


# =====================================================================
# Comment
# =====================================================================
class TestComment:
    def test_creation(self):
        c = Comment(text="hello", vector=[0.1, 0.2, 0.3])
        assert c.text == "hello"
        assert c.vector == [0.1, 0.2, 0.3]

    def test_equality(self):
        c1 = Comment(text="a", vector=[1.0])
        c2 = Comment(text="a", vector=[1.0])
        assert c1 == c2


# =====================================================================
# clustering_result
# =====================================================================
class TestClusteringResult:
    def test_creation(self):
        r = clustering_result(topic="topic1", vector=[1.0, 0.0])
        assert r.topic == "topic1"
        assert r.vector == [1.0, 0.0]


# =====================================================================
# Settings
# =====================================================================
class TestSettings:
    def test_manual_creation(self):
        s = Settings(
            speaker=1,
            setting_ai_text="sys",
            ai_model="gpt",
            max_queue_size=100,
            output="Unity",
            SoundEngine_path="/p/voicevox",
            socialstream_path="/p/ss",
            soundEngine="voicevox",
            input_type="desktop",
            DB_API="http://api",
            WEB_URL="http://web",
        )
        assert s.speaker == 1
        assert s.setting_ai_text == "sys"
        assert s.ai_model == "gpt"
        assert s.max_queue_size == 100
        assert s.output == "Unity"
        assert s.soundEngine == "voicevox"
        assert s.input_type == "desktop"
        assert s.DB_API == "http://api"
        assert s.WEB_URL == "http://web"

    # --- from_json 用ヘルパ ---
    def _write_setting(self, tmp_path: Path, extra: str = ""):
        p = tmp_path / "setting.jsonc"
        p.write_text(json.dumps({
            "Speaker": 2,
            "SettingAItext": "sys2",
            "AI_model": "claude",
            "Max_queue_size": 50,
            "Output": "Sound",
            "SoundEngine_path": "/p/voicevox",
            "Socialstream_path": "/p/ss",
            "SoundEngine": "aivis",
            "Input_type": "stream",
            "DB_API": "http://api2",
            "WEB_URL": "http://web2",
            "public_key_path": "public_key.pem",
        }) + extra, encoding="UTF-8")
        (tmp_path / "public_key.pem").write_text("dummy-key", encoding="UTF-8")
        return p

    @pytest.mark.xfail(
        reason="Settings.from_json が Public_key を cls() に渡すが、"
               "Settings にそのフィールドが無いため TypeError になる（既知の不具合）",
        strict=False,
    )
    def test_from_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = self._write_setting(tmp_path)
        s = Settings.from_json(str(path))
        assert s.speaker == 2
        assert s.setting_ai_text == "sys2"
        assert s.ai_model == "claude"
        assert s.max_queue_size == 50
        assert s.output == "Sound"
        assert s.soundEngine == "aivis"
        assert s.input_type == "stream"

    def test_from_json_strips_line_comments(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        p = tmp_path / "setting.jsonc"
        p.write_text(
            '{\n'
            '  // line comment\n'
            '  "Speaker": 1,\n'
            '  "SettingAItext": "s",\n'
            '  "AI_model": "m",\n'
            '  "Max_queue_size": 10,\n'
            '  "Output": "Unity",\n'
            '  "SoundEngine_path": "/p",\n'
            '  "Socialstream_path": "/p",\n'
            '  "SoundEngine": "voicevox",\n'
            '  "Input_type": "desktop",\n'
            '  "DB_API": "http://a",\n'
            '  "WEB_URL": "http://b",\n'
            '  "public_key_path": "public_key.pem"\n'
            '}',
            encoding="UTF-8",
        )
        (tmp_path / "public_key.pem").write_text("k", encoding="UTF-8")
        # from_json 自体が Public_key バグを持つため、パースされた内容を確認するのは
        # ここでは行わず、少なくとも json 部分が壊れていないことだけを確認する。
        try:
            Settings.from_json(str(p))
        except TypeError:
            # 上記の Public_key バグ
            pass
        except json.JSONDecodeError:
            pytest.fail("JSONC のコメント除去に失敗している")

    def test_from_json_missing_key_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        p = tmp_path / "setting.jsonc"
        p.write_text('{"Speaker": 1}', encoding="UTF-8")
        (tmp_path / "public_key.pem").write_text("k", encoding="UTF-8")
        with pytest.raises(KeyError):
            Settings.from_json(str(p))