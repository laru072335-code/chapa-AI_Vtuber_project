"""
LLMにリクエストを投げるためのファイル
"""
import json
import litellm
import asyncio
import re
import requests
from type_list import *
from database_utilities import Get_content,internet_access

class LLMProvider():
    """
    LLMにリクエストを投げる基本形
    """
    def __init__(self,AImodel:str,settingtext:str,db_url:str,web_url:str):
        """
        ここでシステムプロンプトなどの初期設定の処理をする。
        ここでインターネットに繋がっているかの判定するための関数が欲しい
        """
        self.get_content=Get_content(db_url,web_url)
        self.AImodel=AImodel
        if internet_access():
            responce=requests.get(url=f"{db_url}/system_prompt")
        data=responce.json()
        print(data)
        with open("conversation.json","r+",encoding="UTF-8")as f:
            data=json.load(f)
            if not data[0]["content"][0]["text"] == settingtext:
                data[0]["content"][0]["text"] =settingtext
            f.seek(0)
            json.dump(data,f,ensure_ascii=False)
            f.truncate()
    
    async def create_comment(self,in_q:asyncio.Queue[Message],voice_q:asyncio.Queue,*out_q:asyncio.Queue[Message]):
        """
        応答を生成するためのメソッド
        voice_qには句読点ごとに区切って、またout_qには回答を丸ごと入れる
        """
        #responce_comment=""
        comment_list=[]
        while True:
            prompt = await in_q.get()  
            comments=self.get_content.get_content(prompt.location)
            for comment in comments:
                comment_list.append({"content":[
                {"type":"text","text":prompt.user_name},
                {"type":"text","text":comment.text}
                ],
                "role":"user"})
            comment_list.append({"content":[
                {"type":"text","text":prompt.user_name},
                {"type":"text","text":prompt.content}
                ],
                "role":"user"})
            response=await litellm.acompletion(
                model=self.AImodel,
                messages=comment_list,
                #stream=True
            )
            works=[]
            answer=response.choices[0].message.content
            answers =re.split(r"(?<=[、。？！\s])",answer)
            for q in out_q:
                works.append(asyncio.create_task(q.put(Message(user_name="assistant",content=answer,type=prompt.type,location=prompt.location,stream_id=prompt.stream_id))))
            for ans in answers:
                works.append(asyncio.create_task(voice_q.put(ans)))
                await asyncio.gather(*works)    
            


    def create_summary(self,prompts:list[str])->str:
        """
        クラスタ、配信、ユーザーの傾向などの要約作成のためのもの
        テキストのリストを渡す
        """
        message_list=[]
        for prompt in prompts:
            message_list.append({"content":prompt, "role": "user"})
        message_list.append({"content":"これらの内容を要約して、100字以内にまとめてください。","role":"system"})
        response=litellm.completion(
                model=self.AImodel,
                messages=prompts,
            )
        return response.choices[0].message.content
