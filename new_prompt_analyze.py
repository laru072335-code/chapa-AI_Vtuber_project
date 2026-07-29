"""
-----------------
このファイルではプロンプトに対する様々な分析を行います。
-----------------
"""

import onnxruntime as ort
import sqlite3
import datetime
import pickle
import numpy as np
from tokenizers import Tokenizer
import onnxruntime as ort


def create_onnx_session(model_path):
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

interest_session = create_onnx_session("ModernBERT-basemodel.onnx")
au_session = ort.InferenceSession("emotionToAu_v2.onnx")#このモデルはmpsに載せようとするとエラーが出る、多分opsetのバージョンが18のせい
tokenizer = Tokenizer.from_file("ModernBERT-base_tokenizer.json")

def analyze(sentence,select_table,au=False,test=False):
    """
    ------------
    これでユーザーのプロンプトや、LLMの回答の感情分析などを行えます。
    またそれをanalyze.dbのファイルのselect_tableで指定したテーブルに保管します。
    select_tableで保存するtableを選択
    - user
    ユーザー側のデータを保存
    - assistant 
    アシスタント側のデータを保存
    (将来はユーザーごとに保存)
    auでau_vectorの生成をするかどうかを定義

    testはpytest用、引数auと一緒にTrueにしないこと
    ------------
    """
    global tokenizer
    global au_session
    global interest_session
    print(sentence)
    encoded = tokenizer.encode(sentence)
    ids = encoded.ids
    attention_mask = encoded.attention_mask
    ort_inputs = {
    "input_ids": np.array([ids], dtype=np.int64),
    "attention_mask": np.array([attention_mask], dtype=np.int64)
                }
    output = interest_session.run(["logits","hidden_states"], ort_inputs) # shape (1,6)
    logits=output[0]
    interest=output[1][0]
    binary_interest=pickle.dumps(interest) 
    emotion_probs = np.exp(logits) / np.sum(np.exp(logits), axis=-1, keepdims=True)
    print(f"感情ベクトル:{emotion_probs}")
    #ここから下はクラスタリングする時のためのデータ保存(のちにクラスタリングをすることで興味を推定する。)
    vec=sqlite3.connect("analyze.db")
    cursor=vec.cursor()
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS {select_table} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt TEXT NOT NULL,
        vector BLOB,
        date datetime
    )
    ''')#テーブル作成
    now=datetime.datetime.now().isoformat()
    cursor.execute(f"INSERT INTO {select_table} (prompt,vector,date) VALUES(?,?,?)",(sentence,binary_interest,now))
    vec.commit()
    vec.close()
    au_vector = au_session.run(["AU_vector"], {"emotion_vector": emotion_probs})
    #au_vector= [i.tolist() for i in au_vector]
    au_list=au_vector[0].flatten().tolist()
    au_list=[au_scaling(v) for v in au_list]
    print(f"auベクトル:{au_list}")
    if au:
        return au_list
    if test:
        return au_list,interest,emotion_probs
def au_scaling(v):
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
    analyze(input("にゅうりょくしてください"),)    
