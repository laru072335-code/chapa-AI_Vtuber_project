"""
-----------------
このファイルではプロンプトに対する様々な分析を行います。
-----------------
"""

import onnxruntime as ort
import numpy as np
from tokenizers import Tokenizer
import onnxruntime as ort
import asyncio
from user_database_access import Save_anythings 
from type_list import *


#書き込みの部分を別関数にした方がいいかも(同時に書き込むのを防ぐため)



class Analyze:
    """
    プロンプト分析や、表情生成についてまとめたもの
    tableは開くテーブルの名前
    """
    def __init__(self):
        self.interest_session = self.create_onnx_session("ModernBERT-basemodel.onnx")
        self.au_session = ort.InferenceSession("emotionToAu_v2.onnx")#このモデルはmpsに載せようとするとエラーが出る、多分opsetのバージョンが18のせい
        self.tokenizer = Tokenizer.from_file("ModernBERT-base_tokenizer.json")
        #self.save_class=Save_anythings()

    def create_onnx_session(self,model_path:str) ->ort.InferenceSession:
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

    async def analyze(self,in_q:asyncio.Queue[Message],au_vec_q=False):
        """
        _analyzeに分析する文章を渡して、別スレッドで実行
        """
        loop=asyncio.get_running_loop()
        while True:
            sentence=await in_q.get()
            if au_vec_q:#返り値がある時だけ待つ。
                au_vec=await loop.run_in_executor(None,lambda:self._analyze(sentence,True,False))
                if au_vec_q:
                    await au_vec_q.put(au_vec)
                else:
                    raise ValueError("auがTrueの時、au_vec_qは必要です。")    
            else:
                loop.run_in_executor(None,lambda:self._analyze(sentence))

    def _analyze(self,sentence:Message,au=False,test=False):
        """
        ------------
        これでユーザーのプロンプトや、LLMの回答の感情分析などを行えます。
        auでau_vectorの生成をするかどうかを定義

        testはpytest用、引数auと一緒にTrueにしないこと
        ------------
        """
        encoded = self.tokenizer.encode(sentence.content)
        ids = encoded.ids
        attention_mask = encoded.attention_mask
        ort_inputs = {
        "input_ids": np.array([ids], dtype=np.int64),
        "attention_mask": np.array([attention_mask], dtype=np.int64)
                    }
        output = self.interest_session.run(["logits","hidden_states"], ort_inputs) # shape (1,6)
        logits=output[0]
        interest=output[1]#<class 'numpy.ndarray'>
        emotion_probs = np.exp(logits) / np.sum(np.exp(logits), axis=-1, keepdims=True)
        print(f"感情ベクトル:{emotion_probs}")
        #ここから下はクラスタリングする時のためのデータ保存(のちにクラスタリングをすることで興味を推定する。)
        #v0.3で使用
        #self.save_class.conversation_save(sentence)

        au_vector = self.au_session.run(["AU_vector"], {"emotion_vector": emotion_probs})
        au_list=au_vector[0].flatten().tolist()
        au_list=[self.au_scaling(v) for v in au_list]
        print(f"auベクトル:{au_list}")
        if au:
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
        analyze=Analyze()
        analyze._analyze(Message(input("username"),input("content"),input("location"),input("stream_id")))    
