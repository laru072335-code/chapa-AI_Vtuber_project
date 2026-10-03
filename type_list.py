"""
独自のデータ型や変数の型についてはまとめたもの
"""
import json
import re
from dataclasses import dataclass

@dataclass()
class Message:
    """
    inputの形式について定めたもの
    """
    user_name:str #ユーザーの名前
    content:str #コンテンツ　将来は画像データとかも入る
    type:str #コンテンツのデータがテキストか画像かなどを指定
    location:str #そのコメントの権限について
    stream_id:int=None #配信id

    def __str__(self):
        return f"username{self.user_name}\ncontent{self.content}\nlocation{self.location}\nstream_id{self.stream_id}"
    
    @classmethod
    def to_strs(cls):
        """
        3つの要素に分解するもの
        """
        return cls.user_name,cls.content,cls.location



@dataclass
class Settings:
    """
    設定読み込み用のクラス
    """
    speaker: int
    setting_ai_text: str
    ai_model: str
    max_queue_size: int
    output: str
    SoundEngine_path: str
    socialstream_path: str
    soundEngine : str 
    input_type:str
    DB_API:str
    Public_key:str

    @classmethod
    def from_json(cls, path: str) -> "Settings":
        with open(path, "r", encoding="utf-8") as f:
            content = re.sub(r'//.*', '', f.read())
            data = json.loads(content)
        return cls(
            speaker=int(data["Speaker"]),
            setting_ai_text=data["SettingAItext"],
            ai_model=data["AI_model"],
            max_queue_size=int(data["Max_queue_size"]),
            output=data["output"],
            SoundEngine_path=data["SoundEngine_path"],
            socialstream_path=data["socialstream_path"],
            soundEngine=data["SoundEngine"],
            input_type=data["input_type"],
            DB_API=data["DB_API"],
            public_key=data["public_key"]
        )

@dataclass
class Comment:
    """
    database_accessでコメント（ユーザー)
    """
    text:str
    vector:list[float]

@dataclass
class clustering_result:
    """
    database_accessのclusteringのクラスタの結果
    """
    topic:str
    vector:list[float]
