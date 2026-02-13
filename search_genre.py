import sqlite3, json
import numpy as np
import faiss
from bpemb import BPEmb as BP
conn = sqlite3.connect("data_for_judge.db",check_same_thread=False)# DBからベクトルをロード
cur = conn.cursor()
def unknown_word_classification(prompt):#固有名詞非対応
    cur.execute("SELECT id, vector FROM items")
    rows = cur.fetchall()

    ids = []
    vectors = []
    for id,vector1, in rows:
        ids.append(id)
        vec1 = np.frombuffer(vector1, dtype="float32")
        vectors.append(vec1)

    vectors = np.vstack(vectors)  # (N, d)
    BP_ja =BP(lang="ja", vs=10000, dim=300)#ベクトル生成機
    newvec =np.mean(BP_ja.embed(prompt),axis=0)#未知語のベクトル生成
    newvec = newvec.reshape(1, -1)#変形する
    # FAISSインデックス作成
    index = faiss.IndexFlatIP(300)
    index.add(vectors)
    # クエリ検索
    D, I = index.search(newvec, k=5)

    print("距離:", D)
    #print("候補ID:", [ids[i] for i in I[0]])
    print(I[0][0])
    nearest_term_id =I[0][0]
    cur.execute("SELECT id, smallkey FROM items")
    rows = cur.fetchall()
    print(I[0])
    #for inx in I[0]:#デバッグ用
        #print(rows[inx][1])
    print(rows[nearest_term_id][1])#idで、一番類似度が高いベクトルのidを取得して、そのidの'サブ'ジャンル名を取得している。
    smallkey =rows[nearest_term_id][1]
    cur.execute("SELECT id, bigkey FROM items")
    rows = cur.fetchall()
    print(rows[nearest_term_id][1])#idで、一番類似度が高いベクトルのidを取得して、そのidのジャンル名を取得している。
    bigkey =rows[nearest_term_id][1]
    return  bigkey,smallkey
    
if __name__ =="__main__" :
    unknown_word_classification(input("ワードを入力"))
