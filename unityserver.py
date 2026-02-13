# server.py
import asyncio
import websockets
import queue
import msgpack


#from emotion_AI import emotionAI as AI

start_sign =False
viseme_queue=queue.Queue()
connected = set()
  
async def handler(websocket):
    global start_sign
    print("✅ Unity connected")
    connected.add(websocket)
    try:
        async for message in websocket:
            if message == "start!!":
                 start_sign =True
            print("📩 Unity:", message)#受信
            #ここにパース完了のメッセージ欲しいかも
    except Exception as e:
        print("❌ Unity disconnected")
        print(f"error:{e}")
    finally:
        connected.remove(websocket)
        
async def send_expression_value(): 
    global viseme_queue
    binary_data=None
    viseme_value=None
    while True:
        await asyncio.sleep(0.1) 

        if start_sign:
            try:
                viseme_value= viseme_queue.get_nowait()  
                binary_data=msgpack.packb(viseme_value)
            except:
                viseme_value=None
        #print(viseme_value)
        #print("unity!!!")
        if connected and start_sign and (not viseme_value==None):
            #time.sleep(0.1)#これを入れることで多分あんていしている。
            await asyncio.gather(*(ws.send(binary_data) for ws in connected))
async def main():
    async with websockets.serve(handler, "localhost", 8765)as server:
        print("🚀 Server started on ws://localhost:8765")
        send_task = asyncio.create_task(send_expression_value())
        await server.serve_forever()
        #asyncio.Future()  # サーバーをずっと動かす
def entry_others():
    asyncio.run(main())   
def set_viseme_queue(value):
    global viseme_queue
    viseme_queue.put(value)
if __name__ =="__main__":
    asyncio.run(main())
