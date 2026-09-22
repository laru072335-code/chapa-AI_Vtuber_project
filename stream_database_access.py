"""
場合によってキャッシュかAPIサーバにアクセスするかをコントロールできるようにする。また、キャッシュにはプライベートな会話履歴と、ユーザープロフィール、APIの方にはパブリックな会話履歴、ユーザープロフィールを送信する。
これは配信する側向けのプログラムで、配布するアプリ側はuser_database_accessを参照
"""

import LLM
from type_list import *
from database_access import _clustering
from supabase import create_client, Client
import os

class Accessor():
    """
    クラスタリングをしたり、記憶を参照したりするためのもの
    コメントの保存は、user_database_Accessorで行う
    """
    def __init__(self,llm:LLM.LLMProvider=None):
        supabase: Client = create_client(
                os.environ.get("SUPABASE_URL"),
            os.environ.get("SUPABASE_KEY")
            )
        self.db=stream_database(supabase)
        if not (llm==None):
            self.llm=llm

    def clustering(self,stream_id,stream_name):
        """
        ## クラスタリング(新規作成バージョン)
        ### mode
        - "user" 今日一日分の追加のクラスタリングをする
        - "stream" この配信一回文のクラスタリングをする
        ### con 
        user
        後に日付フィルターも追加してやる。
        また、クラスタリングについてたまに新規作成するようにする
        """
        if self.llm==None:
            raise ValueError("このメソッドを使用する場合はllmの値を入力してください")

        responce=self.db.conversation_load(stream_id)

        if responce.data==[]:
            return "条件にあうデータが存在しません"
        centroid,summary=_clustering(self.llm,responce)
            
        data={
                "stream_id":id,
                "vector":centroid,
                "topics":summary
            }
        self.db.stream_topic_save(data)
        data={
                "stream_id":stream_id,
                "stream_name":stream_name,
                "summary":self.llm.create_summary()
            }
        self.db.stream_topic_save(data)

