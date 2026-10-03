"""
データベースアクセスの基礎部分
"""
from abc import ABC, abstractmethod
import numpy as np
from type_list import *
import sqlite3
from supabase import create_client, Client
import datetime
import os
import requests 
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
        response=self.supabase.table('interest_records').select("text,vector").eq('stream_id',stream_id).execute()
        return response.data

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
            for row in rows:
                return_response.append(Comment(row["text"],rows["vector"]))
            return return_response
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
        if mode=="summary" or mode=="log":
            responce=requests.get(
                            url=f"{self.db_url}/user_comments/{mode}",
                            headers={
                                    "Authorization": f"Bearer {self.token}"
                                    })
            return responce.json()

        else:
            raise ValueError("modeに変な値が入っています。")
