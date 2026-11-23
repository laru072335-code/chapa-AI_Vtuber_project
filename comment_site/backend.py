import os
import asyncio
from dotenv import load_dotenv
from supabase import acreate_client
from dotenv import load_dotenv
from realtime.types import RealtimeSubscribeStates

async def comment(comment,key):
    load_dotenv()
    supabase=await acreate_client(supabase_url=os.environ.get("SUPABASE_URL"),supabase_key=os.environ.get("SUPABASE_KEY"))
    channel = supabase.channel("comment")
    def on_subscribe(status, err):
        if status != RealtimeSubscribeStates.SUBSCRIBED:
            return
    await channel.subscribe(on_subscribe)
    asyncio.create_task(channel.send_broadcast(
        'shout',
        {   "key":key,
            "comment": comment },
    ))
    print("メッセージを送信しました")

async def setting_change(name):
    pass

