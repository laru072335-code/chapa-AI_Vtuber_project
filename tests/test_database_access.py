"""
database_access.py のテスト

注意:
- _clustering / Save_anythings は database_utilities.py 側の責務なのでここでは扱わない
- supabase, requests, login はすべてモックする
- private_database は sqlite3 の :memory: を使う
"""
import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest
from unittest.mock import MagicMock

from database_access import (
    database, stream_database, private_database, public_database,
    DatabaseError, vector_to_float_list,
)
from type_list import Comment, clustering_result


# =====================================================================
# ABC / 例外
# =====================================================================
def test_database_is_abstract():
    with pytest.raises(TypeError):
        database()


def test_database_error_is_exception():
    assert issubclass(DatabaseError, Exception)


# =====================================================================
# private_database
# =====================================================================
@pytest.fixture
def private_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = private_database(":memory:")
    yield db
    try:
        db.end()
    except Exception:
        pass


class TestPrivateDatabase:
    def test_create_table_writes_userprofile(self, private_db):
        private_db.create_table("user1")
        prof_path = Path("userprofile.json")
        assert prof_path.exists()
        prof = json.loads(prof_path.read_text(encoding="UTF-8"))
        assert prof["user_name"] == "user1"
        assert prof["profile_summary"] is None
        assert "last_updated" in prof

    def test_conversation_save_stores_row(self, private_db):
        private_db.create_table("u")
        vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        private_db.conversation_save("hello", vec.tolist(), is_assistant=False)

        private_db.cur.execute(
            "SELECT text, is_assistant FROM interest_records")
        assert private_db.cur.fetchall() == [("hello", 0)]

    def test_conversation_save_assistant_flag(self, private_db):
        private_db.create_table("u")
        private_db.conversation_save("hi", [0.1], is_assistant=True)
        private_db.cur.execute("SELECT is_assistant FROM interest_records")
        assert private_db.cur.fetchone()[0] == 1

    def test_user_get_comment_log_limits_30(self, private_db):
        private_db.create_table("u")
        for i in range(40):
            private_db.conversation_save(f"t{i}", [0.1], is_assistant=False)
        assert len(private_db.user_get_comment("log")) == 30

    def test_user_get_comment_log_is_desc_order(self, private_db):
        private_db.create_table("u")
        private_db.conversation_save("first", [0.1], is_assistant=False)
        private_db.conversation_save("second", [0.1], is_assistant=False)
        result = private_db.user_get_comment("log")
        assert [c.text for c in result] == ["second", "first"]

    @pytest.mark.parametrize("mode", ["summary", "log"])
    def test_user_get_comment_returns_float_list(self, private_db, mode):
        # DBにはfloat32のBLOBで保存されているが、返り値はlist[float]に正規化される
        private_db.create_table("u")
        private_db.conversation_save("hello", [0.1, 0.2, 0.3], is_assistant=False)

        result = private_db.user_get_comment(mode)

        assert len(result) == 1
        comment = result[0]
        assert isinstance(comment, Comment)
        assert isinstance(comment.vector, list)
        assert all(isinstance(v, float) for v in comment.vector)
        assert comment.vector == pytest.approx([0.1, 0.2, 0.3], rel=1e-6)

    def test_user_get_comment_summary_marks_clustered(self, private_db):
        private_db.create_table("u")
        private_db.conversation_save("a", [0.1], is_assistant=False)
        private_db.conversation_save("b", [0.1], is_assistant=False)

        assert len(private_db.user_get_comment("summary")) == 2
        # 2 回目は既に is_clustered = true なので空
        assert private_db.user_get_comment("summary") == []

    def test_user_get_comment_invalid_mode(self, private_db):
        private_db.create_table("u")
        with pytest.raises(ValueError, match="mode"):
            private_db.user_get_comment("nonsense")

    def test_memory_update_writes_profile_and_topics(self, private_db):
        private_db.create_table("u")
        topics = [clustering_result(topic="t1", vector=[1.0, 0.0])]
        private_db.memory_update("summary!", topics)

        prof = json.loads(Path("userprofile.json").read_text(encoding="UTF-8"))
        assert prof["profile_summary"] == "summary!"

        private_db.cur.execute("SELECT topic FROM topic_history")
        assert private_db.cur.fetchone()[0] == "t1"

    def test_end_closes_connection(self, private_db):
        private_db.end()
        with pytest.raises(sqlite3.ProgrammingError):
            private_db.cur.execute("SELECT 1")


# =====================================================================
# stream_database
# =====================================================================
class TestStreamDatabase:
    def _make(self, monkeypatch, data=None):
        fake_client = MagicMock()
        if data is not None:
            (
                fake_client.table.return_value
                .select.return_value
                .eq.return_value
                .execute.return_value
            ) = MagicMock(data=data)
        monkeypatch.setattr(
            "database_access.create_client",
            MagicMock(return_value=fake_client),
        )
        return stream_database(stream_id=7), fake_client

    def test_init_sets_fields(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "http://s")
        monkeypatch.setenv("SUPABASE_KEY", "k")
        fake_client = MagicMock()
        monkeypatch.setattr(
            "database_access.create_client",
            MagicMock(return_value=fake_client),
        )
        db = stream_database(stream_id=42)
        assert db.stream_id == 42
        assert db.supabase is fake_client

    def test_conversation_save_not_implemented(self, monkeypatch):
        db, _ = self._make(monkeypatch)
        with pytest.raises(NotImplementedError):
            db.conversation_save("u", 1, "text", [0.1], "loc")

    def test_memory_update_calls_insert(self, monkeypatch):
        db, fake_client = self._make(monkeypatch)
        topics = [
            clustering_result(topic="T1", vector=[0.1, 0.2]),
            clustering_result(topic="T2", vector=[0.3, 0.4]),
        ]
        db.memory_update(10, "stream-x", "概要", topics)

        tables_used = [c.args[0] for c in fake_client.table.call_args_list]
        assert "stream_summary" in tables_used
        assert "topic_cluster" in tables_used

    def test_user_get_comment_returns_float_list(self, monkeypatch):
        # supabaseがJSON文字列でもlistでも、返り値はlist[float]になる
        db, _ = self._make(monkeypatch, data=[
            {"text": "a", "vector": "[0.1, 0.2]"},
            {"text": "b", "vector": [0.3, 0.4]},
        ])

        result = db.user_get_comment(7)

        assert [c.text for c in result] == ["a", "b"]
        assert result[0].vector == pytest.approx([0.1, 0.2])
        assert result[1].vector == pytest.approx([0.3, 0.4])

    def test_memory_update_sends_json_serializable_vector(self, monkeypatch):
        # postgrest内部のjson=を通るため、ndarrayではなくlist[float]で渡す
        db, fake_client = self._make(monkeypatch)
        topics = [clustering_result(topic="T1", vector=np.array([0.1, 0.2]))]

        db.memory_update(10, "stream-x", "概要", topics)

        inserted = fake_client.table.return_value.insert.call_args.args[0]
        json.dumps(inserted, allow_nan=False)  # 直列化できないとここで失敗する
        assert inserted[0]["topic"] == "T1"
        assert inserted[0]["vector"] == pytest.approx([0.1, 0.2])


# =====================================================================
# public_database
# =====================================================================
class TestPublicDatabase:
    def _make(self, monkeypatch, token="tok", post_json=123, get_json=None):
        monkeypatch.setattr(
            "database_access.login",
            MagicMock(return_value=token),
        )
        fake_post = MagicMock()
        fake_post.return_value.json.return_value = post_json
        fake_get = MagicMock()
        if get_json is not None:
            fake_get.return_value.json.return_value = get_json
        monkeypatch.setattr("database_access.requests.post", fake_post)
        monkeypatch.setattr("database_access.requests.get", fake_get)
        db = public_database("http://api", "http://web")
        return db, fake_post, fake_get

    def test_init_raises_without_token(self, monkeypatch):
        monkeypatch.setattr(
            "database_access.login", MagicMock(return_value=None))
        with pytest.raises(ValueError, match="token"):
            public_database("http://api", "http://web")

    def test_conversation_save_user_with_stream(self, monkeypatch):
        db, fake_post, _ = self._make(monkeypatch, post_json=1)
        db.conversation_save(
            stream_id=1, text="hi", vector=[0.1],
            location="public", is_assistant=False)
        assert fake_post.call_count == 1
        # stream_id ありだと reply_id は更新されない
        assert db.reply_id is None

    def test_conversation_save_user_without_stream_sets_reply_id(
            self, monkeypatch):
        db, _, _ = self._make(monkeypatch, post_json=456)
        db.conversation_save(
            stream_id=None, text="hi", vector=[0.1],
            location="public", is_assistant=False)
        assert db.reply_id == 456

    def test_conversation_save_assistant_requires_reply_id(self, monkeypatch):
        db, _, _ = self._make(monkeypatch, post_json=1)
        with pytest.raises(ValueError, match="reply_id"):
            db.conversation_save(
                stream_id=None, text="ans", vector=[0.1],
                location="public", is_assistant=True)

    def test_conversation_save_assistant_with_reply_id(self, monkeypatch):
        db, fake_post, _ = self._make(monkeypatch, post_json=1)
        db.reply_id = 999
        db.conversation_save(
            stream_id=None, text="ans", vector=[0.1],
            location="public", is_assistant=True)
        payload = fake_post.call_args.kwargs["json"]
        assert payload["reply_id"] == 999
        # 使用後はリセットされる
        assert db.reply_id is None

    def test_user_get_comment_returns_list(self, monkeypatch):
        db, _, _ = self._make(monkeypatch, get_json=[
            {"text": "a", "vector": "[0.1]"},
            {"text": "b", "vector": "[0.2]"},
        ])
        result = db.user_get_comment("log")
        assert [c.text for c in result] == ["a", "b"]
        # APIが返すJSON文字列もlist[float]に正規化される
        assert result[0].vector == pytest.approx([0.1])
        assert result[1].vector == pytest.approx([0.2])

    def test_user_get_comment_accepts_list_vector(self, monkeypatch):
        db, _, _ = self._make(monkeypatch, get_json=[
            {"text": "a", "vector": [0.1, 0.2]},
        ])
        (comment,) = db.user_get_comment("summary")
        assert isinstance(comment, Comment)
        assert comment.vector == pytest.approx([0.1, 0.2])

    def test_user_get_comment_invalid_mode(self, monkeypatch):
        db, _, _ = self._make(monkeypatch)
        with pytest.raises(ValueError, match="mode"):
            db.user_get_comment("xxx")

    def test_memory_update_posts_twice(self, monkeypatch):
        db, fake_post, _ = self._make(monkeypatch)
        topics = [clustering_result(topic="T", vector=[0.1])]
        db.memory_update("summary", topics)
        assert fake_post.call_count == 2

    @pytest.mark.parametrize("vector", [[0.1, 0.2], np.array([0.1, 0.2])])
    def test_memory_update_sends_json_serializable_payload(
            self, monkeypatch, vector):
        # requestsのjson=はstdlibのjson.dumpsなので、素のdict/listにしてから送る
        db, fake_post, _ = self._make(monkeypatch)

        def encode_like_requests(*args, **kwargs):
            json.dumps(kwargs["json"], allow_nan=False)  # 直列化できないと失敗
            return MagicMock()

        fake_post.side_effect = encode_like_requests
        topics = [clustering_result(topic="T", vector=vector)]

        db.memory_update("summary", topics)

        assert fake_post.call_count == 2
        payload = fake_post.call_args_list[0].kwargs["json"]
        assert payload[0]["topic"] == "T"
        assert payload[0]["vector"] == pytest.approx([0.1, 0.2])


# =====================================================================
# vector_to_float_list（Comment.vectorの正規化）
# =====================================================================
class TestVectorToFloatList:
    @pytest.mark.parametrize("raw,expected", [
        # sqliteにfloat32のBLOBで保存したもの
        (np.array([0.1, 0.2, 0.3], dtype=np.float32).tobytes(), [0.1, 0.2, 0.3]),
        # APIが返すJSON文字列
        ("[0.1, 0.2, 0.3]", [0.1, 0.2, 0.3]),
        # すでに数値のリスト / タプル / ndarray
        ([0.1, 0.2, 0.3], [0.1, 0.2, 0.3]),
        ((0.1, 0.2, 0.3), [0.1, 0.2, 0.3]),
        (np.array([0.1, 0.2, 0.3], dtype=np.float32), [0.1, 0.2, 0.3]),
    ])
    def test_normalizes_supported_formats(self, raw, expected):
        result = vector_to_float_list(raw)

        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_none_becomes_empty_list(self):
        assert vector_to_float_list(None) == []
