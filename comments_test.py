"""
任意のコメント取得アプリまたは、それを担うメソッドにコメントを実験的に投げるためのもの
"""

import asyncio
import websockets
import json
import os
from dotenv import load_dotenv
import httpx

load_dotenv()
SESSION_ID = os.getenv("SESSION_KEY") # From your dock.html URL

# あなたのSocial Stream NinjaのセッションIDを設定
# ドキュメントに準拠し、エンドポイントにアクションを含める形に修正
BASE_URL = f"https://io.socialstream.ninja/{SESSION_ID}"


async def send_chat_message(message: str):
    """
    外部のコメントとしてSSNのシステムに流し込む（公式ドキュメントのHTTP POST仕様に準拠）
    """
    # 1. 送信する全体のJSONボディを組み立てる
    # api.md の仕様に基づき、value にはオブジェクトまたは文字列化したJSONを渡します
    payload = {
        "chatname": "ああああ",      # 表示される名前
        "chatmessage": message,         # 本文
        "type": "manual"                # アイコンなどの識別子
    }

    # HTTP POSTのURL（アクションをパスに含める形式、またはルートにJSONを送る形式）
    # api.md: POST/PUT: https://io.socialstream.ninja/SESSION_ID/ACTION
    url = f"https://io.socialstream.ninja/{SESSION_ID}/extContent"

    async with httpx.AsyncClient() as client:
        try:
            # json= 引数を使うことで、正しく application/json でPOSTされます
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                print("-> Comment injected successfully!")
            else:
                print(f"-> Failed to inject comment. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"-> Error injecting comment: {e}")

async def listen_to_chat():
    """
    social streamのコメント取得のテスト
    """
    uri = f"wss://io.socialstream.ninja/join/{SESSION_ID}/4"  # Channel 4 receives chat

    async with websockets.connect(uri) as ws:
        print("Connected! Listening for chat messages...")

        while True:
            message = await ws.recv()
            data = json.loads(message)

            # Chat messages have 'chatname' and 'chatmessage' fields
            if "chatname" in data:
                print(f"[{data.get('type', 'unknown')}] {data['chatname']}: {data.get('chatmessage', '')}")

                # Check for donations
                if data.get('hasDonation'):
                    print(f"  💰 Donation: {data['hasDonation']}")

async def main():
    # 1. チャット欄への一斉送信テスト
    asyncio.create_task(listen_to_chat())
    while True:
        comment = await asyncio.to_thread(input, "送信メッセージを入力: ")
        if comment != "exit2":
            await send_chat_message(comment)
        else:
            break
        await asyncio.sleep(0.3)


# 実行
if __name__ == "__main__":
    asyncio.run(main())
