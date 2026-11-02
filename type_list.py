"""
独自のデータ型や変数の型についてはまとめたもの
"""
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pydantic import BaseModel,field_validator,model_validator
from typing import Literal,Optional
class media_type(StrEnum):
    """
    想定される入力の形式についてまとめたもの
    """
    text="text"
    image="image"
    video="video"
    sound="sound"
    file="file"
class role_type(StrEnum):
    """
    想定される入力の形式についてまとめたもの
    """
    none="none"
    user="user"
    assistant="assistant"
    system="system"#このロールは現在使われていないのでついでに追加しているだけ

class Message(BaseModel):
    """
    inputの形式について定めたもの
    """
    user_name: str  # ユーザーの名前
    content: str  # コンテンツ 将来は画像データとかも入る
    type: Literal["text", "image", "video", "sound", "file"]  # コンテンツのデータがテキストか画像かなどを指定
    authority:Literal["private","public","stream"] #権限設定
    detail:Optional[int|str]=None #publicの場合はdiscordの鯖名とかのより細かい権限について、streamの場合は配信id、privateの場合は何もなし

    @model_validator(mode='after')
    def detail_confirm(self) -> 'Message':
        """authority の値に応じて、必要なフィールドの有無をチェックする"""
        if self.authority == "stream":
            if not isinstance(self.detail,int):
                raise ValueError("authorityが 'stream' の場合、detail(配信id) は必須です。")
        elif self.authority=="private":
            if not self.detail is None:
                raise ValueError("authorityが 'private' の場合、detailはNoneである必要があります。")
        elif self.authority== "public":
            if not isinstance(self.detail,str):
                raise ValueError("authorityが 'public' の場合、detail(詳細な権限情報) は必須です。")
        return self
    
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
    output: str
    SoundEngine_path: str
    socialstream_path: str
    soundEngine : str 
    input_type:str
    Public_key:str
    DB_API:str
    WEB_URL:str

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
            WEB_URL=data["WEB_URL"]
        )

@dataclass
class Comment:
    """
    database_accessでコメント（ユーザー)
    """
    role:role_type #ない場合は明示的にNoneにする。
    text:str
    vector:list[float]
    timestamp:str

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
