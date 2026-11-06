"""
独自のデータ型や変数の型についてはまとめたもの
"""
import json
import re
from dataclasses import dataclass
from pydantic import BaseModel,field_validator
from typing import Literal,Optional

class Message(BaseModel):
    """
    inputの形式について定めたもの
    """
    user_name: str  # ユーザーの名前
    content: str  # コンテンツ 将来は画像データとかも入る
    type: Literal["text", "image", "video", "sound", "file"]  # コンテンツのデータがテキストか画像かなどを指定
    authority:Literal["private","public","stream"] #権限設定
    detail:Optional[int|str]=None #publicの場合はdiscordの鯖名とかのより細かい権限について、streamまたはprivateの場合は未定(今後のために残す)
    
    @field_validator("type")
    @classmethod
    def validate_type_supported(cls, v: str) -> str:
        if v != "text":
            raise ValueError(f"現在 '{v}' タイプは未対応です。'text' のみサポートしています。将来対応させる予定です")
        return v

    @property
    def is_private(self) -> bool:
        return self.authority=="private"

    @property
    def is_public(self) -> bool:
        return self.authority=="public"

    @property
    def is_assistant(self) -> bool:
        return self.user_name == "assistant"

@dataclass
class Settings:
    """
    設定読み込み用のクラス
    """
    speaker: int
    ai_model: str
    max_queue_size: int
    output: Literal["Sound","Unity","Text"]
    SoundEngine_path: str
    socialstream_path: str
    soundEngine : Literal["voicevox","aivis","coeiroink"]
    input_type:Literal["socialstream","discord","desktop","stream"]
    Public_key:str
    DB_API:str
    WEB_URL:str
    stream_id:int
    stream_name:str

    @classmethod
    def from_json(cls, path: str) -> "Settings":
        with open(path, "r", encoding="utf-8") as f:
            content = re.sub(r'(?<!:)\/\/.*', '', f.read())
            data = json.loads(content)
        # type_list.py での読み込みイメージ
        key_path = data.get("public_key_path", "data/public_key.pem")
        public_key_str=""
        with open(key_path, "r", encoding="utf-8") as key_file:
            public_key_str = key_file.read()
        return cls(
            speaker=int(data["Speaker"]),
            ai_model=data["AI_model"],
            max_queue_size=int(data["Max_queue_size"]),
            output=data["Output"],
            SoundEngine_path=data["SoundEngine_path"],
            socialstream_path=data["Socialstream_path"],
            soundEngine=data["SoundEngine"],
            input_type=data["Input_type"],
            DB_API=data["DB_API"],
            Public_key=public_key_str,
            WEB_URL=data["WEB_URL"],
            stream_id=data["stream_id"],
            stream_name=data["stream_name"]
        )

@dataclass
class Comment:
    """
    database_accessでコメント（ユーザー)
    """
    role:Literal["none","user","assistant","system"] #ない場合は明示的にNoneにする。
    text:str
    vector:list[float]
    timestamp:Optional[str]=None

@dataclass
class clustering_result:
    """
    database_accessのclusteringのクラスタの結果
    """
    topic:str
    vector:list[float]

@dataclass
class Profile:
    """
    ユーザーのプロフィール取得用
    """
    user_summary:str
    last_updated:str
