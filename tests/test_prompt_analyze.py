"""
prompt_analyze.py のテスト

- Analyze.__init__ は 2 引数 (db_url, web_url) を取る
- ONNX モデル (ModernBERT-basemodel.onnx / emotionToAu_v2.onnx) と
  tokenizer は実物を読み込む（モックしない）
  * モデルは Analyze 側が相対パスで開くため、ロード中だけ
    prompt_analyze.py のあるディレクトリへ移動する
  * 実モデルが無い / onnxruntime・tokenizers が無い環境では skip する
- DB 保存 (Save_anythings) だけは本番 DB・ネットワークへの副作用を避けるためモックする
- _analyze_and_memory は au=True のときのみ au_list を返す（現行仕様）

実モデルの入出力（実測）:
    ModernBERT-basemodel.onnx : input_ids / attention_mask -> logits (1, 6), hidden_states (768,)
    emotionToAu_v2.onnx       : emotion_vector (1, 6)      -> AU_vector (1, 9)
"""
import asyncio
import copy
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from type_list import Message

INTEREST_MODEL = "ModernBERT-basemodel.onnx"
TOKENIZER_FILE = "ModernBERT-base_tokenizer.json"
AU_MODEL = "emotionToAu_v2.onnx"
MODEL_FILES = (INTEREST_MODEL, TOKENIZER_FILE, AU_MODEL)

EMOTION_CLASSES = 6   # ModernBERT-basemodel.onnx の logits 次元
HIDDEN_SIZE = 768     # ModernBERT-basemodel.onnx の hidden_states 次元
AU_COUNT = 9          # emotionToAu_v2.onnx の AU_vector 次元


def _require_real_dependency(name: str):
    """conftest が MagicMock でスタブした依存を「実物」と誤認しないようにする。"""
    module = pytest.importorskip(name)
    if isinstance(module, MagicMock):
        pytest.skip(f"{name} がスタブされているため実モデルを読み込めません")
    return module


@pytest.fixture(scope="session")
def real_analyze():
    """実 ONNX モデル・実 tokenizer を 1 度だけロードした Analyze を共有する。"""
    _require_real_dependency("onnxruntime")
    _require_real_dependency("tokenizers")

    import prompt_analyze

    root = Path(prompt_analyze.__file__).resolve().parent
    missing = [name for name in MODEL_FILES if not (root / name).exists()]
    if missing:
        pytest.skip(f"モデルファイルが見つかりません: {root} / {', '.join(missing)}")

    # モデル読み込みは相対パスなので、ロード中だけプロジェクトルートへ移動する
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(root)
        with patch("prompt_analyze.Save_anythings", MagicMock()):
            instance = prompt_analyze.Analyze("http://api.local", "http://web.local")
    return instance


@pytest.fixture
def analyze(real_analyze):
    """テストごとに独立した Analyze。重いセッションは共有し、保存先だけ差し替える。"""
    instance = copy.copy(real_analyze)
    instance.save_class = MagicMock()
    return instance


@pytest.fixture
def scaler():
    """au_scaling はモデル不要なので、モデルを読み込む __init__ を介さずに生成する。"""
    import prompt_analyze

    return prompt_analyze.Analyze.__new__(prompt_analyze.Analyze)


def _msg(content="hello", location="private", stream_id=1, user_name="u"):
    return Message(user_name=user_name, content=content, type="text",
                   location=location, stream_id=stream_id)


def _ort_inputs(analyze, text: str) -> dict:
    """tokenizer（実物）で ONNX の入力を作る。"""
    encoded = analyze.tokenizer.encode(text)
    return {
        "input_ids": np.array([encoded.ids], dtype=np.int64),
        "attention_mask": np.array([encoded.attention_mask], dtype=np.int64),
    }


def _direct_interest(analyze, text: str):
    """実モデルへ直接推論させて (logits, hidden_states, probs) を得る。"""
    logits, hidden = analyze.interest_session.run(
        ["logits", "hidden_states"], _ort_inputs(analyze, text)
    )
    probs = np.exp(logits) / np.sum(np.exp(logits), axis=-1, keepdims=True)
    return logits, hidden, probs


# =====================================================================
# au_scaling
# =====================================================================
class TestAuScaling:
    def test_keypoints(self, scaler):
        assert scaler.au_scaling(0.0) == pytest.approx(0.0)
        assert scaler.au_scaling(0.2) == pytest.approx(10.0)
        assert scaler.au_scaling(0.5) == pytest.approx(90.0)
        assert scaler.au_scaling(1.0) == pytest.approx(100.0)

    def test_interpolation(self, scaler):
        # 0.2-0.5 の間は線形補間（10 → 90）
        assert scaler.au_scaling(0.35) == pytest.approx(50.0)
        # 0.0-0.2 の間
        assert scaler.au_scaling(0.1) == pytest.approx(5.0)

    def test_below_zero_is_clamped(self, scaler):
        assert scaler.au_scaling(-0.5) == pytest.approx(0.0)

    def test_above_one_is_clamped(self, scaler):
        assert scaler.au_scaling(2.0) == pytest.approx(100.0)


# =====================================================================
# 実モデルそのものの確認
# =====================================================================
class TestRealModelContract:
    def test_output_dimensions(self, real_analyze):
        logits_out, hidden_out = real_analyze.interest_session.get_outputs()
        assert logits_out.shape[-1] == EMOTION_CLASSES
        assert hidden_out.shape[-1] == HIDDEN_SIZE
        assert real_analyze.au_session.get_outputs()[0].shape[-1] == AU_COUNT

    def test_inference_shapes_and_probabilities(self, real_analyze):
        logits, hidden, probs = _direct_interest(real_analyze, "おはよう")

        assert logits.shape == (1, EMOTION_CLASSES)
        assert hidden.shape == (HIDDEN_SIZE,)
        assert np.all(np.isfinite(hidden))

        assert probs.shape == (1, EMOTION_CLASSES)
        assert probs.sum() == pytest.approx(1.0, rel=1e-5)
        assert np.all(probs > 0.0) and np.all(probs < 1.0)

    def test_au_model_accepts_real_emotion_probs(self, real_analyze):
        _, _, probs = _direct_interest(real_analyze, "おはよう")
        au = real_analyze.au_session.run(["AU_vector"], {"emotion_vector": probs})[0]

        assert au.shape == (1, AU_COUNT)
        assert np.all(np.isfinite(au))
        assert np.all(au >= 0.0) and np.all(au <= 1.0)

    def test_probs_depend_on_text_and_are_deterministic(self, real_analyze):
        _, _, probs_a = _direct_interest(real_analyze, "おはよう")
        _, _, probs_a2 = _direct_interest(real_analyze, "おはよう")
        _, _, probs_b = _direct_interest(real_analyze, "？？？ｗ")

        # 同じ入力なら同じ出力（モックのゼロ埋めではないことの確認も兼ねる）
        np.testing.assert_allclose(probs_a, probs_a2)
        assert not np.allclose(probs_a, 0.0)
        # 入力が違えば出力も変わる = 実際にモデルが推論している
        assert not np.allclose(probs_a, probs_b)


# =====================================================================
# _analyze_and_memory
# =====================================================================
class TestAnalyzeAndMemory:
    def test_au_true_returns_scaled_au_list(self, analyze):
        result = analyze._analyze_and_memory(_msg(), au=True)

        assert isinstance(result, list)
        assert len(result) == AU_COUNT
        assert all(np.isfinite(v) for v in result)
        # au_scaling 適用後なので 0-100 に収まる
        assert all(0.0 <= v <= 100.0 for v in result)
        analyze.save_class.conversation_save.assert_called_once()

    def test_au_list_matches_real_au_model(self, analyze):
        # 実モデルを直接叩いた結果と _analyze_and_memory の出力が一致する
        _, _, probs = _direct_interest(analyze, "hello")
        raw_au = analyze.au_session.run(["AU_vector"], {"emotion_vector": probs})[0]
        expected = [analyze.au_scaling(v) for v in raw_au.flatten().tolist()]

        result = analyze._analyze_and_memory(_msg(), au=True)

        assert result == pytest.approx(expected, abs=1e-4)

    def test_au_false_returns_none_without_touching_au_model(self, analyze, monkeypatch):
        au_spy = MagicMock()
        monkeypatch.setattr(analyze, "au_session", au_spy)

        assert analyze._analyze_and_memory(_msg(), au=False) is None
        au_spy.run.assert_not_called()

    def test_save_class_called_with_message_and_real_hidden_states(self, analyze):
        msg = _msg()
        _, hidden, _ = _direct_interest(analyze, msg.content)

        analyze._analyze_and_memory(msg, au=False)

        call_args = analyze.save_class.conversation_save.call_args
        assert call_args.args[0] is msg
        vector = call_args.args[1]
        assert isinstance(vector, list)
        assert len(vector) == HIDDEN_SIZE
        assert all(np.isfinite(v) for v in vector)
        # 実モデルの hidden_states がそのまま保存される
        assert vector == pytest.approx(hidden.tolist(), abs=1e-5)

    def test_test_mode_with_au_returns_au_list(self, analyze):
        # 現行仕様: au=True が先に return するため test=True でも au_list のみ
        result = analyze._analyze_and_memory(_msg(), au=True, test=True)

        assert isinstance(result, list)
        assert len(result) == AU_COUNT

    @pytest.mark.xfail(
        reason="au=False かつ test=True のとき au_list 未定義で UnboundLocalError"
               "（既知の不具合）",
        strict=False,
    )
    def test_test_mode_without_au(self, analyze):
        analyze._analyze_and_memory(_msg(), test=True)


# =====================================================================
# analyze_and_memory (async)
# =====================================================================
class TestAnalyzeAndMemoryAsync:
    @pytest.mark.asyncio
    async def test_no_au_just_calls_internal(self, analyze):
        called = []
        analyze._analyze_and_memory = MagicMock(
            side_effect=lambda m, *a, **k: called.append(m))

        in_q = asyncio.Queue()
        await in_q.put(_msg())

        task = asyncio.create_task(analyze.analyze_and_memory(in_q))
        for _ in range(50):
            if called:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(called) == 1

    @pytest.mark.asyncio
    async def test_with_au_pushes_to_queue(self, analyze):
        analyze._analyze_and_memory = MagicMock(return_value=[0.5] * AU_COUNT)

        in_q, au_q = asyncio.Queue(), asyncio.Queue()
        await in_q.put(_msg())

        task = asyncio.create_task(analyze.analyze_and_memory(in_q, au_q))
        result = await asyncio.wait_for(au_q.get(), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert result == [0.5] * AU_COUNT

    @pytest.mark.asyncio
    async def test_real_model_au_vector_is_pushed_to_queue(self, analyze):
        in_q, au_q = asyncio.Queue(), asyncio.Queue()
        await in_q.put(_msg())

        task = asyncio.create_task(analyze.analyze_and_memory(in_q, au_q))
        try:
            result = await asyncio.wait_for(au_q.get(), timeout=120)
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        assert len(result) == AU_COUNT
        assert all(0.0 <= v <= 100.0 for v in result)
