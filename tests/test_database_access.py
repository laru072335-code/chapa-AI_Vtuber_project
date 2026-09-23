import asyncio
import json
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from database_access import (
    _clustering, database, Save_anythings,
)


# ---------- _clustering ----------
def test_clustering_no_llm_raises():
    with pytest.raises(ValueError):
        _clustering(None, [])


def test_clustering_too_few_raises():
    llm = MagicMock()
    data = [{"text": "a", "vector": json.dumps([1.0, 0.0])}] * 3
    with pytest.raises(ValueError, match="コメント数が少ない"):
        _clustering(llm, data)


def test_clustering_basic(monkeypatch):
    # hdbscan.HDBSCAN をモック
    mock_hdbscan = MagicMock()
    mock_clusterer = MagicMock()
    mock_clusterer.fit_predict.return_value = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
    mock_hdbscan.HDBSCAN.return_value = mock_clusterer
    monkeypatch.setattr("database_access.hdbscan", mock_hdbscan)

    llm = MagicMock()
    llm.create_summary.return_value = "summary"

    data = []
    for i in range(5):
        data.append({"text": f"a{i}", "vector": json.dumps([1.0, 0.0])})
    for i in range(5):
        data.append({"text": f"b{i}", "vector": json.dumps([0.0, 1.0])})

    result = _clustering(llm, data)
    assert len(result) == 2
    for r in result:
        assert "topics" in r
        assert isinstance(r["vector"], np.ndarray)
        # クラスタ重心は正規化されている
        assert np.linalg.norm(r["vector"]) == pytest.approx(1.0, rel=1e-5)
    # 各クラスタで 1 回ずつ summary が呼ばれる
    assert llm.create_summary.call_count == 2


def test_clustering_skips_noise_label(monkeypatch):
    mock_hdbscan = MagicMock()
    mock_clusterer = MagicMock()
    # -1 はノイズ
    mock_clusterer.fit_predict.return_value = np.array([-1, -1, 0, 0, 0, 0, 0])
    mock_hdbscan.HDBSCAN.return_value = mock_clusterer
    monkeypatch.setattr("database_access.hdbscan", mock_hdbscan)

    llm = MagicMock()
    llm.create_summary.return_value = "s"
    data = [{"text": f"t{i}", "vector": json.dumps([1.0, 0.0])} for i in range(7)]
    result = _clustering(llm, data)
    assert len(result) == 1


# ---------- database (ABC) ----------
def test_database_is_abstract():
    with pytest.raises(TypeError):
        database()


# ---------- private_database ----------
@pytest.fixture
def private_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from database_access import private_database
    db = private_database(":memory:")
    yield db
    try:
        db.end()
    except Exception:
        pass


def test_private_database_create_table(private_db):
    private_db.create_table("user1")
    assert Path("userprofile.json").exists()
    prof = json.loads(Path("userprofile.json").read_text(encoding="UTF-8"))
    assert prof["user_name"] == "user1"
    assert prof["profile_summary"] is None


def test_private_database_conversation_save(private_db):
    private_db.create_table("u")
    vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    private_db.conversation_save("hello", vec)
    # SELECT で確認
    private_db.cur.execute("SELECT text FROM interest_records")
    rows = private_db.cur.fetchall()
    assert rows[0][0] == "hello"


def test_private_database_memory_update(private_db):
    private_db.create_table("u")
    topics = [{"topics": "t1", "vector": np.array([1.0, 0.0], dtype=np.float32)}]
    private_db.memory_update("summary!", topics)
    prof = json.loads(Path("userprofile.json").read_text(encoding="UTF-8"))
    assert prof["profile_summary"] == "summary!"


# ---------- Save_anythings ----------
def test_save_anythings_routing_public(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from database_access import Save_anythings
    sa = Save_anythings("http://x")
    sa.public_database = MagicMock()
    sa.private_database = MagicMock()

    from type_list import Message
    msg = Message("u", "hi", "public:1", 1)
    sa.conversation_save(msg, np.array([0.1]))
    sa.public_database.conversation_save.assert_called_once()
    sa.private_database.conversation_save.assert_not_called()


def test_save_anythings_routing_private(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from database_access import Save_anythings
    sa = Save_anythings("http://x")
    sa.public_database = MagicMock()
    sa.private_database = MagicMock()

    from type_list import Message
    msg = Message("u", "hi", "private", 1)
    sa.conversation_save(msg, np.array([0.1]))
    sa.public_database.conversation_save.assert_not_called()
    sa.private_database.conversation_save.assert_called_once()


def test_save_anythings_unknown_location(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from database_access import Save_anythings
    sa = Save_anythings("http://x")
    sa.public_database = MagicMock()
    sa.private_database = MagicMock()

    from type_list import Message
    msg = Message("u", "hi", "unknown", 1)
    with pytest.raises(ValueError, match="location"):
        sa.conversation_save(msg, np.array([0.1]))
