"""
データベースアクセスの基礎部分
"""
from abc import ABC, abstractmethod
import numpy as np
import json
from type_list import *
import sqlite3
from supabase import create_client, Client
import datetime
import os
import requests 
from public_database_login import login
class DatabaseError(Exception):
    pass

def vector_to_float_list(vector)->list[float]:
    """
    DB/APIごとに異なるベクトル表現を list[float] に正規化する
    - bytes/bytearray/memoryview: sqliteにfloat32のBLOBで保存したもの
    - str: APIが返すJSON文字列(例:"[0.1, 0.2]")
    - list/tuple/np.ndarray: そのままfloatのリストへ
    """
    if vector is None:
        return []
    if isinstance(vector,(bytes,bytearray,memoryview)):
        return np.frombuffer(bytes(vector),dtype=np.float32).tolist()
    if isinstance(vector,str):
        vector=json.loads(vector)
    return [float(v) for v in vector]

class database(ABC):
    """
    データベースにアクセスする時の基本形
    エラーの場合はDataBaseErrorを返す。
    """
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def conversation_save(self,user_name:str,stream_id:int,text:str,vector:list[float],location:str):
        """
        会話内容を保存する
        """

    @abstractmethod
    def user_get_comment(self,mode:str)->list[Comment]:
        """
        クラスタリングまたは、短期記憶に使用するログを取得する\n
        modeは、要約のためのコメント取得なのか、短期記憶(ログ)のためのものなのか指定する
        - summaryと入力すると、要約用(DBのis_clusteredタグをTrueにする)
        - logと入力すると、短期記憶(ログ)用(直近30件)
        Comment.vectorは保存形式(bytes/JSON文字列)によらず常にlist[float]で返す
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
    def __init__(self,stream_id:int):
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

    def user_get_comment(self,stream_id:int)->list[Comment]:
        """
        配信に対するデータ処理をするときは、stream_idで取得する方法のみに対応(場合分けする必要がないため)
        """
        response=self.supabase.table('interest_records').select("text,vector").eq('stream_id',stream_id).execute()
        return [Comment(data["text"],vector_to_float_list(data["vector"])) for data in response.data]

    def memory_update(self,stream_id:int,stream_name:str,stream_summary:str,topic_data:list[clustering_result]):
        data={
                "stream_id":stream_id,
                "stream_name":stream_name,
                "summary":stream_summary
            }
        self.supabase.table('stream_summary').insert(data).execute()
        # topic_clusterもpostgrest内部のjson=を通るため、素のdict/listへ変換する
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

    def create_table(self,user_name:str):
        """
        新しく保存用のファイルを作る
        そのファイルがすでにあるかの判定もする
        """
        self.cur.execute("""
        CREATE TABLE interest_records (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        text TEXT NOT NULL,
        vector BLOB,
        is_clustered BOOL DEFAULT FALSE,
        is_assistant BOOL NOT NULL);
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


    def conversation_save(self,text:str,vector:list[float],is_assistant:bool):
        vector_bytes = np.array(vector, dtype=np.float32).tobytes()
        self.cur.execute("INSERT INTO interest_records (text,vector,is_assistant) VALUES (?,?,?)", (text, vector_bytes,is_assistant))
        self.conn.commit()
    
    def memory_update(self,user_summary:str,topic_data:list[clustering_result]):
        with open("userprofile.json","r+",encoding="UTF-8")as f:
            data=json.load(f)
            data["profile_summary"]=user_summary
            data["last_updated"]=datetime.datetime.now().isoformat()
            f.seek(0)
            json.dump(data,f)
            f.truncate()
        data = [(topics.topic, np.array(topics.vector, dtype=np.float32).tobytes())
                for topics in topic_data]
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

    def user_get_comment(self,mode:str)->list[Comment]:
        if mode=="summary":
            self.cur.execute("SELECT text, vector FROM interest_records WHERE is_clustered = false")
            rows =self.cur.fetchall()
            self.cur.execute("UPDATE interest_records SET is_clustered = true WHERE is_clustered = false")
            # BLOB(float32)をlist[float]に戻して返す
            return [Comment(row[0],vector_to_float_list(row[1]))for row in rows]
        elif mode=="log":
            self.cur.execute(
                "SELECT text, vector FROM interest_records "
                "ORDER BY timestamp DESC, record_id DESC LIMIT 30")
            rows =self.cur.fetchall()
            return [Comment(row[0],vector_to_float_list(row[1]))for row in rows]
        else:
            raise ValueError("modeに変な値が入っています。")


class public_database(database):
    """
    パブリックな会話履歴などを保存するためのもの
    """
    def __init__(self,db_url:str,web_url:str):
        self.db_url=db_url
        self.token=login(web_url)
        self.reply_id=None
        if not self.token:
            raise ValueError("tokenを取得できませんでした。")

    def conversation_save(self,stream_id:int,text:str,vector:list[float],location:str,is_assistant:bool):
        if is_assistant and stream_id==None:
            if self.reply_id:
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
                                            "location": location,
                                            "reply_id":self.reply_id
                                            })
                self.reply_id=None
            else:
                raise ValueError("AIの会話記録をDBに保存するとき、reply_idが必要です")
        else:
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
                            "location": location,
                            "reply_id":None
                            })
            if not stream_id:
                self.reply_id=int(responce.json())
    
    def memory_update(self,user_summary:str,topic_data:list[clustering_result]):
        payload=[{"topic":t.topic,"vector":t.vector} for t in topic_data]
        responce=requests.post(
                        url=f"{self.db_url}/user_topic_save",
                        headers={
                                "Authorization": f"Bearer {self.token}"
                                }
                        ,json=payload)
        responce=requests.post(
                                url=f"{self.db_url}/user_profile_update",
                                headers={
                                        "Authorization": f"Bearer {self.token}"
                                        }
                                ,json={"profile_summary":user_summary})
    
    def search(self,**con):
        pass

    def user_get_comment(self,mode:str)->list[Comment]:
        if mode=="summary" or mode=="log":
            responce=requests.get(
                            url=f"{self.db_url}/user_comments/{mode}",
                            headers={
                                    "Authorization": f"Bearer {self.token}"
                                    })
            return_json=responce.json()
            return [Comment(data["text"],vector_to_float_list(data["vector"])) for data in return_json]

        else:
            raise ValueError("modeに変な値が入っています。")

if __name__=="__main__":
    db=public_database("https://chapa-api-three.vercel.app","https://commentsite.vercel.app")
    #db.create_table("aaa")
    #db.conversation_save() これはprompt_analyzeからテストしたほうがいいかも
    p=db.user_get_comment("log")
    print(len(p))
    print(type(p[0].vector))
    #db.memory_update()
    #db.search()
