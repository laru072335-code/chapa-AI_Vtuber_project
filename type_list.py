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
    user_name:str
    content:str
    location:str
    stream_id:int=None

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
    sd_default_device: str
    SoundEngine_path: str
    socialstream_path: str
    LLM_Tool : str
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
            sd_default_device=data["sd.default.device"],
            SoundEngine_path=data["SoundEngine_path"],
            socialstream_path=data["socialstream_path"],
            LLM_Tool=data["LLM_Tool"],
            soundEngine=data["SoundEngine"],
            input_type=data["input_type"],
            DB_API=data["DB_API"],
            public_key=data["public_key"]
        )
