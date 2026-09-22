"""
場合によってキャッシュかAPIサーバにアクセスするかをコントロールできるようにする。また、キャッシュにはプライベートな会話履歴と、ユーザープロフィール、APIの方にはパブリックな会話履歴、ユーザープロフィールを送信する。
これは配布アプリ向けのプログラムで、配信する側はstream_database_accessを参照
"""
import sqlite3
import json
import datetime
import numpy as np
import LLM
from database_access import _clustering
from database_access import *

from type_list import *
        
class Accessor():
    """
    記憶に保存したり、記憶を参照したりするためのもの
    """
    def __init__(self,llm:LLM.LLMProvider):
        self.private_database=private_database("memory.db")
        self.public_database=public_database()

    def clustering(self,con):
        """
        ## クラスタリング(新規作成バージョン)

        ### con 
        user
        後に日付フィルターも追加してやる。
        また、クラスタリングについてたまに新規作成するようにする
        """
        if self.llm==None:
            raise ValueError("このメソッドを使用する場合はllmの値を入力してください")
        responce=supabase.table('interest_records').select('text','vector').eq('user_id',id).execute()
    
        if responce.data==[]:
            return "条件にあうデータが存在しません"
        _clustering(self.llm,responce)
                #ここでstreamidを投げれてない
        data={
                    "user_id":id,
                    "vector":centroid.astype(np.float32).tolist(),
                    "topics":self.llm.create_summary()
                }
        supabase.table('topic_history').insert(data).execute()
                #この間でollamaに投げる
        supabase.table('user_profile').update({"profile_summary":""}).eq("user_id",id).execute()

    def conversation_save(self,data:Message):
            """
            publicかprivateかどっちのデータベースに送ればいいのか判定する。
            適したデータベースに保存する。
            """
            if data.location=="public":
                self.public_database
            elif data.location=="private":
                self.private_database
            else:
                raise ValueError("locationに不明な値があります。")
                    



