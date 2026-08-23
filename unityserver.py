"""
-----
unity側に様々なデータを送るためのファイル
-----
"""
import asyncio
import websockets
import msgpack
import numpy as np
from type_list import *

class unityserver:
    """
    送信処理や、その前の整形、接続確立などを担当
    """
    def __init__(self,responce_queue :asyncio.Queue=None):
        self.connected = set()
        if responce_queue is not None:
            self.responce_queue=responce_queue#非同期キュー
        else:
            self.responce_queue=None
    
    async def handler(self,websocket):
        """
        ------
        接続確立用
        ------
        """
        print("✅ Unity connected")
        self.connected.add(websocket)
        try:
            async for message in websocket:
                if message is not None:
                    if self.responce_queue is not None:
                        await self.responce_queue.put(message)
                    print("📩 Unity:", message)#受信
                #ここにパース完了のメッセージ欲しいかも
        except Exception as e:
            print("❌ Unity disconnected")
            print(f"error:{e}")
        finally:
            self.connected.remove(websocket)

    async def send_viseme(self,in_q:asyncio.Queue):
        """
        visemeの送信
        """
        while True:
            viseme_list=await in_q.get()
            await self._send_data(0,viseme_list)

    async def send_subtitle(self,prompt_in_q:asyncio.Queue[Message],answer_in_q:asyncio.Queue[Message]):
        """
        字幕の送信
        """
        while True:
            subtitle_prompt=await prompt_in_q.get()
            subtitle_answer=await answer_in_q.get()
            subtitle=[subtitle_prompt.content,subtitle_answer.content]
            await self._send_data(1,subtitle)

    async def send_au(self,in_q :asyncio.Queue):
        """
        auの送信
        """
        while True:
            au_vector= await in_q.get()
            await self._send_data(2,au_vector)

    async def send_sound(self,in_q :asyncio.Queue):
        """
        音の送信
        """
        while True:
            sound= await in_q.get()
            data, rate = sound 
            data_bytes = data.astype(np.float32).tobytes()
            await self._send_data(3, [rate, data_bytes])
            
    async def _send_data(self,head:int ,data):
        """
        ヘッダをつけて送る用
        """
        binary_data=msgpack.packb([head,data])  
        print(f"データがおくられました!! header={head}")
        #print(data)
        await asyncio.gather(*(ws.send(binary_data) for ws in self.connected))


    async def main(self,test=False):
        """
        -----
        サーバーを動かすためのエントリーポイント
        -----
        """
        server = await websockets.serve(self.handler, "127.0.0.1", 8765)
        print("🚀 Server started on ws://127.0.0.1:8765")
        print("conntcedが出るまで接続されていません。")
        try:
            # サーバーが終了しないように無限に待機する
            if test:
                await asyncio.sleep(10)
            else:
                await asyncio.Future() 
        finally:
            server.close()
            await server.wait_closed()

#単体テスト用
if __name__ =="__main__":
    unityserver1=unityserver()
    asyncio.run(unityserver1.main())
