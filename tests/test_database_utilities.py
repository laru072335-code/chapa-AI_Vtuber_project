"""
database_utilities.py のテスト

テスト方針:
- 外部 I/O（ソケット、DB、LLM）はすべて MagicMock / AsyncMock で差し替える
- グローバル変数 public_database_instant はフィクスチャでリセットする
"""
import asyncio
import json
import numpy as np
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

import database_utilities
from database_access import private_database
from database_utilities import (
    internet_access, Save_anythings, Get_content, Clustering,
)
from type_list import Message, Comment, clustering_result


# =====================================================================
# フィクスチャ
# =====================================================================
@pytest.fixture
def clear_global():
    """グローバル状態を毎回リセット"""
    database_utilities.public_database_instant = None
    yield
    database_utilities.public_database_instant = None


@pytest.fixture
def mocked_dbs(monkeypatch, clear_global):
    """private_database と public_database をモック化"""
    fake_private = MagicMock()
    fake_public = MagicMock()
    monkeypatch.setattr("database_utilities.private_database",
                        MagicMock(return_value=fake_private))
    monkeypatch.setattr("database_utilities.public_database",
                        MagicMock(return_value=fake_public))
    return fake_private, fake_public


# =====================================================================
# internet_access
# =====================================================================
class TestInternetAccess:
    def _patch_socket(self, monkeypatch, connect_side_effect):
        class FakeSocket:
            def __init__(self, *a, **k):
                pass

            def connect(self, addr):
                if isinstance(connect_side_effect, Exception):
                    raise connect_side_effect

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        monkeypatch.setattr("database_utilities.socket.socket", FakeSocket)
        monkeypatch.setattr("database_utilities.socket.setdefaulttimeout",
                            lambda t: None)

    def test_returns_true_on_success(self, monkeypatch):
        self._patch_socket(monkeypatch, connect_side_effect=None)
        assert internet_access() is True

    def test_returns_false_on_oserror(self, monkeypatch):
        self._patch_socket(monkeypatch, connect_side_effect=OSError("no net"))
        assert internet_access() is False

    def test_default_arguments(self, monkeypatch):
        captured = {}

        class FakeSocket:
            def __init__(self, family, type_):
                captured["family"] = family
                captured["type"] = type_

            def connect(self, addr):
                captured["addr"] = addr

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        monkeypatch.setattr("database_utilities.socket.socket", FakeSocket)
        monkeypatch.setattr("database_utilities.socket.setdefaulttimeout",
                            lambda t: None)

        assert internet_access() is True
        assert captured["addr"] == ("1.1.1.1", 53)


# =====================================================================
# Save_anythings
# =====================================================================
class TestSaveAnythings:
    def test_creates_public_db_when_global_is_none(self, monkeypatch, clear_global):
        fake_private = MagicMock()
        fake_public = MagicMock()
        pd_cls = MagicMock(return_value=fake_public)

        monkeypatch.setattr("database_utilities.private_database",
                            MagicMock(return_value=fake_private))
        monkeypatch.setattr("database_utilities.public_database", pd_cls)

        sa = Save_anythings("http://api", "http://web")
        pd_cls.assert_called_once_with("http://api", "http://web")
        assert sa.private_database is fake_private
        assert sa.public_database is fake_public
        assert database_utilities.public_database_instant is fake_public

    def test_reuses_global_public_db(self, monkeypatch, clear_global):
        fake_private = MagicMock()
        fake_public = MagicMock()
        database_utilities.public_database_instant = fake_public
        pd_cls = MagicMock()

        monkeypatch.setattr("database_utilities.private_database",
                            MagicMock(return_value=fake_private))
        monkeypatch.setattr("database_utilities.public_database", pd_cls)

        sa = Save_anythings("http://api", "http://web")
        pd_cls.assert_not_called()
        assert sa.public_database is fake_public

    def test_conversation_save_public_user(self, mocked_dbs):
        fake_private, fake_public = mocked_dbs
        sa = Save_anythings("http://api", "http://web")
        msg = Message(user_name="u", content="hi", type="text",
                      location="public", stream_id=1)
        sa.conversation_save(msg, [0.1, 0.2])
        fake_public.conversation_save.assert_called_once_with(
            1, "hi", [0.1, 0.2], "public", False)
        fake_private.conversation_save.assert_not_called()

    def test_conversation_save_public_assistant(self, mocked_dbs):
        fake_private, fake_public = mocked_dbs
        sa = Save_anythings("http://api", "http://web")
        msg = Message(user_name="assistant", content="hi", type="text",
                      location="public", stream_id=1)
        sa.conversation_save(msg, [0.1])
        fake_public.conversation_save.assert_called_once_with(
            1, "hi", [0.1], "public", True)

    def test_conversation_save_private_user(self, mocked_dbs):
        fake_private, fake_public = mocked_dbs
        sa = Save_anythings("http://api", "http://web")
        msg = Message(user_name="u", content="hi", type="text",
                      location="private", stream_id=None)
        sa.conversation_save(msg, [0.1])
        fake_private.conversation_save.assert_called_once_with("hi", [0.1], False)
        fake_public.conversation_save.assert_not_called()

    def test_conversation_save_private_assistant(self, mocked_dbs):
        fake_private, _ = mocked_dbs
        sa = Save_anythings("http://api", "http://web")
        msg = Message(user_name="assistant", content="hi", type="text",
                      location="private", stream_id=None)
        sa.conversation_save(msg, [0.1])
        fake_private.conversation_save.assert_called_once_with("hi", [0.1], True)

    def test_conversation_save_unknown_location_raises(self, mocked_dbs):
        sa = Save_anythings("http://api", "http://web")
        msg = Message(user_name="u", content="hi", type="text",
                      location="unknown", stream_id=None)
        with pytest.raises(ValueError, match="location"):
            sa.conversation_save(msg, [0.1])


# =====================================================================
# Get_content
# =====================================================================
class TestGetContent:
    def test_get_private(self, mocked_dbs):
        fake_private, _ = mocked_dbs
        fake_private.user_get_comment.return_value = ["log1"]
        gc = Get_content("http://api", "http://web")
        assert gc.get_content("private") == ["log1"]
        fake_private.user_get_comment.assert_called_with("log")

    def test_get_private_with_subpath(self, mocked_dbs):
        fake_private, _ = mocked_dbs
        fake_private.user_get_comment.return_value = []
        gc = Get_content("http://api", "http://web")
        gc.get_content("private:xyz")
        fake_private.user_get_comment.assert_called_with("log")

    def test_get_public(self, mocked_dbs):
        _, fake_public = mocked_dbs
        fake_public.user_get_comment.return_value = ["log2"]
        gc = Get_content("http://api", "http://web")
        assert gc.get_content("public") == ["log2"]
        fake_public.user_get_comment.assert_called_with("log")

    def test_get_unknown_raises(self, mocked_dbs):
        gc = Get_content("http://api", "http://web")
        with pytest.raises(ValueError, match="location"):
            gc.get_content("unknown")


# =====================================================================
# Clustering._clustering
# =====================================================================
class TestClustering:
    def _patch_hdbscan(self, monkeypatch, labels):
        mock_clusterer = MagicMock()
        mock_clusterer.fit_predict.return_value = np.array(labels)
        mock_hdbscan = MagicMock()
        mock_hdbscan.HDBSCAN.return_value = mock_clusterer
        monkeypatch.setattr("database_utilities.hdbscan", mock_hdbscan)
        return mock_clusterer

    def test_no_llm_raises(self):
        with pytest.raises(ValueError, match="llm"):
            Clustering()._clustering(None, [])

    def test_too_few_data_raises(self):
        llm = MagicMock()
        data = [Comment("a", [1.0, 0.0]) for _ in range(3)]
        with pytest.raises(ValueError, match="コメント数が少ない"):
            Clustering()._clustering(llm, data)

    def test_basic_clustering(self, monkeypatch):
        self._patch_hdbscan(monkeypatch, [0] * 5 + [1] * 5)

        llm = MagicMock()
        llm.create_summary.return_value = "summary"

        data = [Comment(f"a{i}", [1.0, 0.0]) for i in range(5)]
        data += [Comment(f"b{i}", [0.0, 1.0]) for i in range(5)]

        result = Clustering()._clustering(llm, data)
        assert len(result) == 2
        for r in result:
            assert isinstance(r, clustering_result)
            # 重心はlist[float]（memory_updateがjson=へ渡せる形）
            assert isinstance(r.vector, list)
            assert all(isinstance(v, float) for v in r.vector)
            # 重心は正規化されている
            assert np.linalg.norm(r.vector) == pytest.approx(1.0, rel=1e-5)
        # 各クラスタで 1 回ずつ summary 生成
        assert llm.create_summary.call_count == 2

    def test_noise_label_skipped(self, monkeypatch):
        self._patch_hdbscan(monkeypatch, [-1, -1, 0, 0, 0, 0, 0])
        llm = MagicMock()
        llm.create_summary.return_value = "s"
        data = [Comment(f"t{i}", [1.0, 0.0]) for i in range(7)]
        result = Clustering()._clustering(llm, data)
        assert len(result) == 1

    def test_summary_receives_texts_of_each_cluster(self, monkeypatch):
        self._patch_hdbscan(monkeypatch, [0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        llm = MagicMock()
        llm.create_summary.return_value = "s"

        data = [Comment("x", [1.0, 0.0]) for _ in range(5)]
        data += [Comment("y", [0.0, 1.0]) for _ in range(5)]

        Clustering()._clustering(llm, data)
        # 2 回呼ばれ、それぞれ list[str] を受け取る
        assert llm.create_summary.call_count == 2
        for call in llm.create_summary.call_args_list:
            (arg,) = call.args
            assert isinstance(arg, list)
            assert all(isinstance(s, str) for s in arg)

    def test_json_string_vector_raises(self):
        # Comment.vectorはlist[float]が前提（JSON文字列は受け付けない）
        llm = MagicMock()
        data = [Comment("a", "[1.0, 0.0]")]
        with pytest.raises(TypeError, match=r"list\[float\]"):
            Clustering()._clustering(llm, data)

    def test_result_is_json_serializable(self, monkeypatch):
        # memory_update が requests / supabase の json= にそのまま渡せる形か
        self._patch_hdbscan(monkeypatch, [0] * 5)
        llm = MagicMock()
        llm.create_summary.return_value = "s"
        data = [Comment(f"t{i}", [1.0, 0.0]) for i in range(5)]

        result = Clustering()._clustering(llm, data)

        json.dumps([{"topic": r.topic, "vector": r.vector} for r in result],
                   allow_nan=False)


# =====================================================================
# private_database -> Clustering の結合（Comment.vectorの正規化）
# =====================================================================
class TestClusteringWithPrivateDatabase:
    def test_clustering_accepts_private_db_comments(self, tmp_path, monkeypatch):
        # user_get_comment が返す Comment をそのまま _clustering に渡せる
        monkeypatch.chdir(tmp_path)
        db = private_database(":memory:")
        db.create_table("u")
        for i in range(5):
            db.conversation_save(f"t{i}", [1.0, 0.0], is_assistant=False)

        data = db.user_get_comment("summary")
        assert len(data) == 5

        mock_clusterer = MagicMock()
        mock_clusterer.fit_predict.return_value = np.array([0] * 5)
        fake_hdbscan = MagicMock()
        fake_hdbscan.HDBSCAN.return_value = mock_clusterer
        monkeypatch.setattr("database_utilities.hdbscan", fake_hdbscan)

        llm = MagicMock()
        llm.create_summary.return_value = "summary"

        result = Clustering()._clustering(llm, data)
        db.end()

        assert len(result) == 1
        assert np.allclose(result[0].vector, [1.0, 0.0])