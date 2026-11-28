"""
-----------------
このファイルではプロンプトに対する様々な分析を行います。
-----------------
"""
import sys
import onnxruntime as ort
import numpy as np
from tokenizers import Tokenizer
import onnxruntime as ort
import asyncio
from database_utilities import Save_anythings
from type_list import *
from error_handle import run_with_error_handling

class Analyze:
    """
    プロンプト分析や、表情生成についてまとめたもの
    tableは開くテーブルの名前
    db_urlは外部のデーターベースに保存するときのAPIのurl
    """
    def __init__(self,db_url:str,web_url:str,stream_id:int):
        self.interest_session = self._create_onnx_session("data/embedding_model.onnx")
        self.au_session = ort.InferenceSession("data/emotionToAu_v2.onnx")#このモデルはmpsに載せようとするとエラーが出る、多分opsetのバージョンが18のせい
        self.tokenizer = Tokenizer.from_file("data/embeddinggemma-2.json")
        self.save_class=Save_anythings(db_url,web_url,stream_id)

    def _create_onnx_session(self,model_path:str) ->ort.InferenceSession:
        """
        自動でGPUかCPUかMシリーズかを判定して効率よくインターセッションを作るもの
        """
        available = ort.get_available_providers()
        providers = []
        #RTX専用
        if 'CUDAExecutionProvider' in available:
            providers.append('CUDAExecutionProvider')
        # Mac環境
        if 'CoreMLExecutionProvider' in available:
            providers.append('CoreMLExecutionProvider')
        # Windows環境
        elif 'DmlExecutionProvider' in available:
            providers.append('DmlExecutionProvider')
        # CPU
        providers.append('CPUExecutionProvider')
        return ort.InferenceSession(model_path, providers=providers)

    def generate_vector(self,content:str):
        encoded = self.tokenizer.encode(f"task: clustering | input:{content}")
        ids = encoded.ids
        attention_mask = encoded.attention_mask
        ort_inputs = {
        "input_ids": np.array([ids], dtype=np.int64),
        "attention_mask": np.array([attention_mask], dtype=np.int64)
                    }
        output = self.interest_session.run(["logits","embeddings"], ort_inputs) # shape (1,6)
        #print(output)
        logits=output[0]# 感情ベクトル
        interest=output[1][0]# 興味ベクトル
        shifted_logits = logits - np.max(logits, axis=-1, keepdims=True)#オーバーフロー対策
        emotion_probs = np.exp(shifted_logits) / np.sum(np.exp(shifted_logits), axis=-1, keepdims=True)
        print(f"感情ベクトル:{emotion_probs}")
        #ここから下はクラスタリングする時のためのデータ保存(のちにクラスタリングをすることで興味を推定する。)
        # データベース保存をメインループへ安全に投げ、例外をキャッチできるようにする
        print(f"興味ベクトル:{len(interest.tolist())}")
        return (emotion_probs,interest)

    async def analyze_and_memory(self,in_q:asyncio.Queue[Message],au_vec_q=False):
        """
        _analyzeに分析する文章を渡して、別スレッドで実行
        """
        loop=asyncio.get_running_loop()
        while True:
            sentence=await in_q.get()
            if au_vec_q:#返り値がある時だけ待つ。
                au_vec=await loop.run_in_executor(
                    None,
                    run_with_error_handling,
                    self._analyze_and_memory,
                    loop,
                    sentence,
                    True,
                    False)
                await au_vec_q.put(au_vec)
            else:
                await loop.run_in_executor(
                    None,
                    run_with_error_handling,  
                    self._analyze_and_memory,
                    loop,
                    sentence)

    def _analyze_and_memory(self,loop,sentence:Message,au=False,test=False)->list[float]:
        """
        これでユーザーのプロンプトや、LLMの回答の感情分析などを行えます。
        auでau_vectorの生成をするかどうかを定義

        testはpytest用、引数auと一緒にTrueにしないこと
        """
        emotion_probs,interest=self.generate_vector(sentence.content)
        future = asyncio.run_coroutine_threadsafe(self.save_class.conversation_save(sentence, interest.tolist()),loop)

          # コルーチン内でエラーが起きた場合にコンソールへトレースバックを表示するコールバック
        def handle_future_result(f):
            try:
              f.result()  # ここで例外があればスローされる
            except Exception as e:
              import traceback

              print(
                  "--- conversation_save 内部でエラーが発生しました ---",
                  file=sys.stderr,
              )
              traceback.print_exc()

        future.add_done_callback(handle_future_result)

        if au:
            au_vector = self.au_session.run(["AU_vector"], {"emotion_vector": emotion_probs})
            au_list=au_vector[0].flatten().tolist()
            au_list=[self.au_scaling(v) for v in au_list]
            print(f"auベクトル:{au_list}")
            return au_list
        
        if test:
            return au_list,interest,emotion_probs
        
    def au_scaling(self,v)->float:
        """
        返り値として受け取ったAUの値を増幅する
        """
        # 入力の基準点
        input_pts = [0.0, 0.2, 0.5, 1.0]
        # 出力の基準点（0.2~0.5の間を0.1~0.9に大きく広げる）
        output_pts = [0.0, 0.1, 0.9, 1.0]
        return 100*float(np.interp(v, input_pts, output_pts))

#単体テスト用
if __name__=="__main__":
    import threading
    from dotenv import load_dotenv

    load_dotenv()

    # 設定ファイルの読み込み（実物）
    setting_data = Settings.from_json("data/setting.jsonc")

    print("=== Analyze インスタンス初期化（実物） ===")
    analyze = Analyze(setting_data.DB_API, setting_data.WEB_URL, setting_data.stream_id)
    print("初期化成功\n")

    # 実物の非同期イベントループを別スレッドで開始
    # （_analyze_and_memory 内部の asyncio.run_coroutine_threadsafe が安全に実行されるようにする）
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()

    try:
        test_msg = Message(
            user_name="ああああ",
            content="最新のAI技術やプログラミング言語にとても興味があります！",
            type="text",
            authority="stream"
        )
        au_list, interest, emotion_probs = analyze._analyze_and_memory(loop, test_msg)

    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2.0)
        
