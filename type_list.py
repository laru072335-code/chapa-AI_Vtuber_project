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
            content = re.sub(r'(?<!:)\/\/.*', '', f.read())
            data = json.loads(content)
        # type_list.py での読み込みイメージ
        key_path = data.get("public_key_path", "public_key.pem")
        public_key_str=""
        with open(key_path, "r", encoding="utf-8") as key_file:
            public_key_str = key_file.read()
        return cls(
            speaker=int(data["Speaker"]),
            setting_ai_text=data["SettingAItext"],
            ai_model=data["AI_model"],
            max_queue_size=int(data["Max_queue_size"]),
            output=data["Output"],
            SoundEngine_path=data["SoundEngine_path"],
            socialstream_path=data["Socialstream_path"],
            soundEngine=data["SoundEngine"],
            input_type=data["Input_type"],
            DB_API=data["DB_API"],
            Public_key=public_key_str
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
