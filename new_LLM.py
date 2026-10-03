"""
LLMにリクエストを投げるためのファイル
"""
import json
import litellm
import asyncio
import re
import requests
from type_list import *
from database_utilities import Get_content

class LLMProvider():
    """
    LLMにリクエストを投げる基本形
    """
    def __init__(self,AImodel,settingtext,db_url):
        """
        ここでシステムプロンプトなどの初期設定の処理をする。
        """
        self.get_content=Get_content(db_url)
        self.AImodel=AImodel
        responce=requests.get(url=f"{db_url}/system_prompt")
        data=responce.json()
        print(data)
        with open("conversation.json","r+",encoding="UTF-8")as f:
            data=json.load(f)
            if not data[0]["content"]["text"] == settingtext:
                data[0]["content"]["text"] =settingtext
            f.seek(0)
            json.dump(data,f,ensure_ascii=False)
            f.truncate()
    
    async def create_comment(self,in_q:asyncio.Queue[Message],voice_q:asyncio.Queue,*out_q:asyncio.Queue[Message]):
        """
        応答を生成するためのメソッド
        voice_qには句読点ごとに区切って、またout_qには回答を丸ごと入れる
        """
        responce_comment=""
        while True:
            prompt = await in_q.get()  
            short_memory=self.get_content.get_content(prompt.location)
            short_memory.append({"content": prompt.content, "name":prompt.user_name,"role":"user"})
            response=await litellm.acompletion(
                model=self.model,
                messages=short_memory,
                stream=True
            )
            async for chunk in response:
                print(responce_comment+chunk.choices[0].delta.content)
                print(chunk.choices[0].delta.content or "", end="")
            


    def create_summary(self,prompts:list)->str:
        """
        クラスタ、配信、ユーザーの傾向などの要約作成のためのもの
        promptsはget_content
        """
        responce=litellm.completion(
            model=self.model,
            messages=prompts,
            stream=True
        )

            
class OllamaProvider(LLMProvider):
    """
    Ollamaでリクエストを投げるためのもの
    """
       
    async def create_comment(self,in_q:asyncio.Queue[Message],voice_q:asyncio.Queue,*out_q:asyncio.Queue[Message]):
        """
        create_taskのための関数、これは別スレッドに回すので、ここではloopを取得して本体の関数を実行
        """
        loop=asyncio.get_running_loop()
        while True:
            prompt = await in_q.get()  
            prompt_str=f"{prompt.user_name}\n{prompt.content}"
            answer=await loop.run_in_executor(None,lambda:self._ollama_LLM_comments(prompt_str)) 
            #voice用にリスト化して高速化
            answers =re.split(r"(?<=[、。？！\s])",answer)
            answers = [s.strip() for s in answers if s.strip()]
            print(answers)
            works=[]
            for q in out_q:
               works.append(asyncio.create_task(q.put(Message("assistant",answer,prompt.location,prompt.stream_id))))
            for ans in answers:
                works.append(asyncio.create_task(voice_q.put(ans)))
            await asyncio.gather(*works)    


