from dotenv import load_dotenv
import os
import asyncio
import websockets
import json
from abc import ABC, abstractmethod
from type_list import *
from supabase import acreate_client
from dotenv import load_dotenv
import jwt
       

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
        self.session_key=os.getenv("SESSION_KEY")

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
                        await q.put(Message(user_name=user_name,content=content,location=self.location,stream_id=self.stream_id)) 

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

    async def is_ready(self):
        pass

class Desktop_input(Input_format):
    def __init__(self):
        super().__init__("private")
        pass

    async def latest_get_comment(self,*out_q : asyncio.Queue[Message]):
        pass

    async def is_ready(self):
        pass 

class Stream_input(Input_format):
    """

    """
    def __init__(self, stream_id):
        super().__init__(stream_id,"pulblic")
        self.jwt_key=os.environ.get("JWT_KEY")

    async def latest_get_comment(self,*out_q : asyncio.Queue[Message]):
        def recive(payload):
            """
            コメントを受け取った時の処理
            """
            try:
                contents = jwt.decode(payload['key'], self.jwt_key, algorithms=["HS256"])

                user_id = contents.get("sub")
                user_name = contents.get("name")

                for q in out_q:
                    q.put(Message(user_name=user_name,content=payload["comment"],location="public",stream_id=self.stream_id)) 

            except jwt.ExpiredSignatureError:
                print("エラー: トークンの有効期限（exp）が切れています")
            except jwt.InvalidTokenError:
                print("エラー: トークンが改ざんされているか、秘密鍵が異なります")
        self.channel.on_broadcast(
            event="shout",
            callback=recive
        ).subscribe()
        await asyncio.sleep(10)

    async def is_ready(self):
        supabase=await acreate_client(os.environ.get("COMMENT_SUPABASE_URL"),os.environ.get("COMMENT_SUPABASE_KEY"))
        self.channel = supabase.channel("comment")
        return True

"""
このコードは通信のテスト用
"""
async def main():
    load_dotenv()
    supabase=await acreate_client(supabase_url=os.environ.get("COMMENT_SUPABASE_URL"),supabase_key=os.environ.get("COMMENT_SUPABASE_KEY"))
    # 1. チャンネルを作成
    channel = supabase.channel("comment")
    def message_received(payload):
        print(f"Broadcast received: {payload}")
    await channel.on_broadcast('shout',message_received).subscribe()
    asyncio.create_task(channel.send_broadcast(
        'shout',
        { "message": 'hello, world' },
    ))
    print("メッセージを送信しました")

    # プログラムが終了しないように待機
    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())


if __name__=="__main__":
    pass
    #out_q=asyncio.Queue[Message]()
    #stream_input=Stream_input(1)
    #stream_input.latest_get_comment(out_q)
