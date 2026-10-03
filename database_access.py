"""
データベースアクセスの基礎部分
"""
from abc import ABC, abstractmethod
import numpy as np
import hdbscan
import new_LLM
from type_list import *
import sqlite3
from supabase import create_client, Client
import datetime
import os
import requests 



def _clustering(llm:new_LLM.LLMProvider,data:list[Comment])->list[clustering_result]:
    """
    ## クラスタリング(新規作成バージョン)
    ベクトルデータを渡すとクラスタリングする
    - llm LLMを内部で使用するためのインスタンスを渡す
    返り値は、{"topic":summary,"vector":centroid}のリスト
    """
    return_list=[]
    if llm==None:
        raise ValueError("このメソッドを使用する場合はllmの値を入力してください")
    recive_vector=[i.vector for i in data]#ベクトルデータだけをとりだす。
    recive_text=[i.text for i in data]#テキストデータだけ取り出す
    vectors= [json.loads(i) for i in recive_vector]#ベクトルデータをnumpy型に変換(str->float->numpy)
    vectors=np.array(vectors,dtype=np.float32)
    
    if vectors.shape[0] <5:
        raise ValueError("エラー：元となるコメント数が少ないです。")
            
    normalized_vectors = vectors / np.linalg.norm(vectors,axis=1,keepdims=True)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=5,metric='euclidean',prediction_data=True)
    labels = clusterer.fit_predict(normalized_vectors) 
    kind_labels=set(labels)

    for label in kind_labels:
        if label==-1:
            continue
        cluster_vecs = normalized_vectors[labels == label]
        cluster_items = [text for text, l in zip(recive_text, labels) if l == label]
        centroid = np.mean(cluster_vecs, axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        summary=llm.create_summary(cluster_items)
        return_list.append(clustering_result(summary,centroid))
    return return_list

def stream_clustering(llm:new_LLM.LLMProvider,stream_id:int,stream_name:str):
    """
    配信データのクラスタリング
    """
    database=stream_database()
    data=database.user_get_comment()
    stream_summary=llm.create_summary([i["text"]for i in data])
    clustering_result=_clustering(llm,data)
    database.memory_update(stream_id,stream_name,stream_summary,clustering_result)

def user_clustering(llm:new_LLM.LLMProvider,db_url:str):
    """
    ユーザーデータのクラスタリング
    """
    database1=public_database(db_url,)
    data:list=database1.user_get_comment("summary")
    clustering_result=_clustering(llm,data)
    user_summary=llm.create_summary([i["text"]for i in data])
    database1.memory_update(user_summary,clustering_result)

    database2=private_database()
    data2=database2.user_get_comment("summary")
    data.extend(data2)
    user_summary=llm.create_summary([i["text"]for i in data])
    clustering_result=_clustering(llm,data)
    database2.memory_update(user_summary,clustering_result)



class DatabaseError(Exception):
    pass
class database(ABC):
    """
    データベースにアクセスする時の基本形
    エラーの場合はDataBaseErrorを返す。
    """
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def conversation_save(self,user_name:str,stream_id:int,text:str,vector:np.ndarray,location:str):
        """
        会話内容を保存する
        """

    @abstractmethod
    def user_get_comment(self,mode:str)->list[Comment]:
        """
        クラスタリングまたは、短期記憶に使用するログを取得する\n
        modeは、要約のためのコメント取得なのか、短期記憶(ログ)のためのものなのか指定する
        - summaryと入力すると、要約用
        - logと入力すると、短期記憶(ログ)用(直近30件)
        """
        pass

    @abstractmethod
    def memory_update(self):
        """
        クラスタリングした結果をデータベースに反映する
        """
        pass

    @abstractmethod
    def search(self,**con):
        """
        LLMが検索する時用
        """
        pass


class stream_database(database):
    """
    配信側用のデータ保存
    """
    def __init__(self,stream_id):
        self.stream_id=stream_id
        self.supabase: Client = create_client(
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_KEY")
        )

    def conversation_save(self, user_name, stream_id, text, vector, location):
        """
        streamモードの会話保存はpublic_databaseクラスで行う
        """
        raise NotImplementedError

    def user_get_comment(self,stream_id:int):
        """
        配信に対するデータ処理をするときは、stream_idで取得する方法のみに対応(場合分けする必要がないため)
        """
        return self.supabase.table('interest_records').select("text,vector").eq('stream_id',stream_id).execute()

    def memory_update(self,stream_id:int,stream_name:str,stream_summary:str,topic_data:list[clustering_result]):
        data={
                "stream_id":stream_id,
                "stream_name":stream_name,
                "summary":stream_summary
            }
        self.supabase.table('stream_summary').insert(data).execute()
        data=[]
        for topic in topic_data:
            data.append({
                "topic":topic.topic,
                "vector":topic.vector,
            })

        self.supabase.table('topic_cluster').insert(data).execute()

    def search(self,**con):
        pass
        
class private_database(database):
    """
    プライベートな会話履歴などを保存するためのデータベース
    """
    def __init__(self,dbname:str):
        self.conn = sqlite3.connect(dbname)
        self.cur = self.conn.cursor()

    def create_table(self,user_name):
        """
        新しく保存用のファイルを作る
        そのファイルがすでにあるかの判定もする
        """
        self.cur.execute("""
        CREATE TABLE interest_records (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        text TEXT NOT NULL,
        vector BLOB);
            """)
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS topic_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        vector BLOB NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);
        """)
        self.conn.commit()
        with open("userprofile.json","w",encoding="UTF-8")as f:
            data={
                "user_name":user_name,
                "last_updated":datetime.datetime.now().isoformat(),
                "profile_summary":None

            }
            json.dump(data,f)


    def conversation_save(self,text:str,vector:np.ndarray):
        self.cur.execute("INSERT INTO interest_records (text,vector) VALUES (?, ?)", (text, vector))
        self.conn.commit()
    
    def memory_update(self,user_summary:str,topic_data:list[clustering_result]):
        with open("userprofile.json","r+",encoding="UTF-8")as f:
            data=json.load(f)
            data["profile_summary"]=user_summary
            data["last_updated"]=datetime.datetime.now().isoformat()
            f.seek(0)
            json.dump(data,f)
            f.truncate()
        data = [(topics.topic, topics.vector) for topics in topic_data]
        self.cur.executemany("INSERT INTO topic_history (topic, vector) VALUES (?, ?)",data)
        self.conn.commit()
    
    def search(self,**con):
        pass
            
    def end(self):
        """
        最後にファイルを閉じる時に実行
        """
        self.conn.commit()
        self.conn.close()

    def user_get_comment(self,mode:str):
        return_response=[]
        if mode=="summary":
            self.cur.execute("SELECT text, vector FROM interest_records WHERE created_at >= datetime('now', '-24 hours');")
            rows =self.cur.fetchall()
            for row in rows:
                return_response.append(Comment(row["text"],rows["vector"]))

            return return_response
        elif mode=="log":
            self.cur.execute("SELECT text, vector FROM interest_records WHERE created_at >= datetime('now', '-24 hours');")
            rows =self.cur.fetchall()
            return rows
        else:
            raise ValueError("modeに変な値が入っています。")


class public_database(database):
    """
    パブリックな会話履歴などを保存するためのもの
    """
    def __init__(self,db_url,token=None):
        self.db_url=db_url
        self.token=token

    def conversation_save(self,user_name:str,stream_id:int,text:str,vector:np.ndarray,location:str):
        responce=requests.post(
                    url=f"{self.db_url}/conversation_save",
                    headers={
                            "Authorization": f"Bearer {self.token}"
                            }
                    ,
                    json={
                        "stream_id": stream_id,
                        "text": text,
                        "vector":vector ,
                        "location": location
                        })
    
    def memory_update(self,user_summary:str,topic_data:list[clustering_result]):

        responce=requests.post(
                        url=f"{self.db_url}/user_topic_save",
                        headers={
                                "Authorization": f"Bearer {self.token}"
                                }
                        ,json=topic_data)
        responce=requests.post(
                                url=f"{self.db_url}/user_profile_update",
                                headers={
                                        "Authorization": f"Bearer {self.token}"
                                        }
                                ,json={"profile_summary":user_summary})
    
    def search(self,**con):
        pass

    def user_get_comment(self,mode:str):
        if mode=="summary":
            responce=requests.get(
                            url=f"{self.db_url}/user_get_comments",
                            headers={
                                    "Authorization": f"Bearer {self.token}"
                                    })
            return responce.json()
        elif mode=="log":
            responce=requests.get(
                            url=f"{self.db_url}/user_get_comments",
                            headers={
                                    "Authorization": f"Bearer {self.token}"
                                    })
            return responce.json()
        else:
            raise ValueError("modeに変な値が入っています。")

    
class Save_anythings():
    """
    会話を自動で適切な保存領域に保存するためのもの
    """
    def __init__(self,db_url):
        self.private_database=private_database("memory.db")
        self.public_database=public_database(db_url)

    def conversation_save(self,data:Message,vector):
        """
        publicかprivateかどっちのデータベースに送ればいいのか判定する。
        適したデータベースに保存する。
        """
        if data.location.startswith("public"):
            self.public_database.conversation_save(data.user_name,data.stream_id,data.content,vector,data.location)
        elif data.location.startswith("private"):
            self.private_database.conversation_save(data.content,vector)
        else:
            raise ValueError("locationに不明な値があります。")

class Get_content():
    """
    短期記憶を確保するためのもの
    """
    def __init__(self,db_url):
        self.private_database=private_database("memory.db")
        self.public_database=public_database(db_url)

    def get_content(self,location:str)->list[dict]:
        if location.startswith("private"):
            private_comment_list=self.private_database.user_get_comment("log")
            public_comment_list=self.public_database.user_get_comment("log")
        elif location.startswith("public"):
            public_comment_list=self.public_database.user_get_comment("log")
        else:
            raise ValueError("locationに不明な値があります")
   
if __name__=="__main__":
    private_database1=private_database("memory.db")
    public_database1=public_database("https://chapa-api-three.vercel.app")
    
