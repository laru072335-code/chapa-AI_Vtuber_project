"""
データベースに関数操作について個別にクラスにまとめたユーティリティ
"""
from database_access import private_database,public_database,stream_database
from type_list import *
import hdbscan
import numpy as np
import socket
import json
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:# Clusteringクラスの型チェックのため
    import new_LLM

def internet_access(host: str = "1.1.1.1", port: int = 53, timeout: float = 3.0) -> bool: 
    """
    1.1.1.1 の 53番ポート（DNS）にTCP接続を試みる
    """
    try:
        socket.setdefaulttimeout(timeout)
        # ソケットを作成して接続テスト
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            return True
    except OSError:
        return False
    
class Save_anythings():
    """
    会話を自動で適切な保存領域に保存するためのもの
    """
    def __init__(self,db_url:str,web_url:str):
        self.private_database=private_database("data/memory.db")
        self.save_id=asyncio.Queue[int](maxsize=10) #とりあえず10
        self.public_database=public_database(db_url,web_url)

    async def conversation_save(self,data:Message,vector:list[float]):
        """
        publicかprivateかどっちのデータベースに送ればいいのか判定する。
        適したデータベースに保存する。
        """
        loop=asyncio.get_running_loop()
        if data.is_public:
            if data.is_assistant:
                save_id=await self.save_id.get()
                if save_id:
                    await loop.run_in_executor(None,lambda:self.public_database.conversation_save(data.stream_id,data.content,vector,data.authority,save_id))
                   
                else:
                    raise ValueError("assistantの回答は必ずuserの回答の後にDBに保存する必要があります")
            else:
                temp=await loop.run_in_executor(None,lambda:self.public_database.conversation_save(data.stream_id,data.content,vector,data.authority,False))
                await self.save_id.put(temp)

        elif data.is_private:
            if data.is_assistant:
                await loop.run_in_executor(None,lambda: self.private_database.conversation_save(data.content,vector,True))
               
            else:
                await loop.run_in_executor(None,lambda:self.private_database.conversation_save(data.content,vector,False))
                
        else:
            raise ValueError("authorityに不明な値があります。")

class Get_content():
    """
    短期記憶を確保するためのもの
    """
    def __init__(self,db_url:str,web_url:str):
        self.private_database=private_database("data/memory.db")
        self.public_database=public_database(db_url,web_url)

    def get_content(self,authority:str):
        if authority=="private":
            self.private_database.user_get_comment("log")
            self.public_database.user_get_comment("log")
        elif authority=="public":# publicの場合もう少し細かく分ける必要があるかも？
            return self.public_database.user_get_comment("log")
        else:
            raise ValueError("authorityに不明な値があります")

    def get_user_profile(self,authority:str):
        """
        ユーザーのプロフィールを取得する。
        """
        if authority=="private":
            self.private_database.get_profile()
        elif authority=="public":# publicの場合もう少し細かく分ける必要があるかも？
            return self.public_database.get_profile()
        else:
            raise ValueError("authorityに不明な値があります")
        

class Clustering:
    """
    クラスタリング処理についてまとめたもの
    """
    def _clustering(self,llm:"new_LLM.LLMProvider",data:list[Comment])->list[clustering_result]:
        """
        ## クラスタリング(新規作成バージョン)
        ベクトルデータを渡すとクラスタリングする
        - llm LLMを内部で使用するためのインスタンスを渡す
        返り値は、{"topic":summary,"vector":centroid}のリスト
        """
        return_list=[]
        if llm==None:
            raise ValueError("このメソッドを使用する場合はllmの値を入力してください")
        # Comment.vectorはlist[float]（user_get_commentで正規化済み）
        if not all(isinstance(i.vector,(list,tuple,np.ndarray)) for i in data):
            raise TypeError("Comment.vectorはlist[float]である必要があります")
        recive_vector=[i.vector for i in data]#ベクトルデータだけをとりだす。
        recive_text=[i.text for i in data]#テキストデータだけ取り出す
        vectors=np.array(recive_vector,dtype=np.float32)
        
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
            return_list.append(clustering_result(summary,centroid.tolist()))
        return return_list

    def stream_clustering(self,llm:"new_LLM.LLMProvider",stream_id:int,stream_name:str):
        """
        配信データのクラスタリング
        """
        database=stream_database(stream_id)
        data=database.user_get_comment(stream_id)
        stream_summary=llm.create_summary([i.text for i in data])
        clustering_result=self._clustering(llm,data)
        database.memory_update(stream_id,stream_name,stream_summary,clustering_result)

    def user_clustering(self,llm:"new_LLM.LLMProvider",db_url:str,web_url:str):
        """
        ユーザーデータのクラスタリング
        """
        global public_database_instant
        if public_database_instant:
            database1=public_database_instant
        else:
            database1=public_database(db_url,web_url)
            public_database_instant=database1
        data=database1.user_get_comment("summary")
        clustering_result=self._clustering(llm,data)
        user_summary=llm.create_summary([i.text for i in data])
        database1.memory_update(user_summary,clustering_result)

        database2=private_database("data/memory.db")
        data2=database2.user_get_comment("summary")
        data.extend(data2)
        user_summary=llm.create_summary([i.text for i in data])
        clustering_result=self._clustering(llm,data)
        database2.memory_update(user_summary,clustering_result)

if __name__=="__main__":
    print(internet_access())
    #private_database1=private_database("memory.db")
    #public_database1=public_database("https://chapa-api-three.vercel.app")
    
