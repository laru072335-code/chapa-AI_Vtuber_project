from dotenv import load_dotenv
import os
import asyncio
import websockets
import json
from abc import ABC, abstractmethod
from type_list import *

class Input_format(ABC):
    @abstractmethod
    def __init__(self,stream_id,location:str):
        """
        特殊な場合を除き、public かprivateで指定する
        """
        self.location=location
        self.stream_id=stream_id
        
    @abstractmethod
    async def latest_get_comment(self,*out_q : asyncio.Queue[Message]):
        """
        コメントなどを取得するためのもの
        """
        pass
    @abstractmethod
    async def is_ready(self):
        """
        起動したかの確認
        """
        pass

class socialstream_input(Input_format):
    """
    ここに様々なものをシステムに流し込むための、準備をする。
    """
    def __init__(self,stream_id):
        super().__init__(stream_id,"public")
        load_dotenv()
        self.session_key=os.getenv("SESSON_KEY")

    async def latest_get_comment(self,*out_q : asyncio.Queue[Message]):
        """
        social stream に対してWebSocketによるコメント取得
        多分絵文字がコメントに含まれるとバグる
        """
        uri = f"wss://io.socialstream.ninja/join/{self.session_key}/4" 

        async with websockets.connect(uri) as ws:
            print("Connected! Listening for chat messages...")
            while True:
                message = await ws.recv()
                data = json.loads(message)
                if "chatname" in data:
                    content=data.get('chatmessage', '')
                    user_name=data['chatname']
                    for q in out_q:
                        await q.put(Message(user_name,content,self.location,self.stream_id)) 

    async def is_ready(self):
        uri = f"wss://io.socialstream.ninja/join/{self.session_key}/4" 
        try:
            async with websockets.connect(uri):
                return True
        except:
            return False


class Discord_input(Input_format):
    def __init__(self):
        super().__init__("public")
        pass

    async def latest_get_comment(self,*out_q : asyncio.Queue[Message]):
        pass

class Desktop_input(Input_format):
    def __init__(self):
        super().__init__("private")
        pass

    async def latest_get_comment(self,*out_q : asyncio.Queue[Message]):
        pass
