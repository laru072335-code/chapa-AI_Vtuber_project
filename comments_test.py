"""
任意のコメント取得アプリまたは、それを担うメソッドにコメントを実験的に投げるためのもの
"""

import asyncio
import websockets
import json
import os
from dotenv import load_dotenv
"""Social Streamからコメント取得"""
"""responceの例
{'chatname': 'Steve_830970394883', 
'nameColor': '#107516', 
'chatbadges': '',
'backgroundColor': '',
'textColor': '', 
'chatmessage': "!join The only way 2 do great work is to love what you do. If you haven't found it yet, keep looking. Don't settle. As with all matters of the heart, you'll know when you find it.",
'chatimg': '',
'type': 'slack', 
'hasDonation': '',
'membership': 'SPONSORSHIP',
'id': 5055,
'timestamp': 1780895846391,
'containsBadWords': False}
"""
load_dotenv()
SESSION_ID = os.getenv("SESSON_KEY") # From your dock.html URL

import asyncio
import httpx

# あなたのSocial Stream NinjaのセッションIDを設定
BASE_URL = f"https://io.socialstream.ninja/{SESSION_ID}"


async def send_chat_message(message: str):
    """
    外部のコメントとしてSSNのシステムに流し込む（公式ドキュメントのPOST仕様に準拠）
    """
    import json

    # 1. まず、内側のチャットデータ（オブジェクト）を作る
    comment_data = {
        "chatname": "MyManualBot",      # 表示される名前
        "chatmessage": message,         # 本文
        "type": "manual"                # アイコンなどの識別子
    }

    # 2. 【重要】ドキュメントの仕様通り、内側のデータを一度「JSON文字列」に変換する
    stringified_value = json.dumps(comment_data)

    # 3. 送信する全体のJSONボディを組み立てる
    payload = {
        "action": "extContent",
        "value": stringified_value  # 文字列化したデータを渡す
    }

    # 4. 【重要】POSTのURLはセッションIDまで（末尾に action や null は不要）
    url = f"https://io.socialstream.ninja/{SESSION_ID}"

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
        if comment!="exit2":
            await send_chat_message(comment)
        else:
            break
        await asyncio.sleep(0.3)



# 実行
if __name__ == "__main__":
    asyncio.run(main())


