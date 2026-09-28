"""
LLMにリクエストを投げるためのファイル
"""
from abc import ABC, abstractmethod
import json
import litellm
import asyncio
import re
import requests
from type_list import *
import copy
from database_access import Get_content

class LLMProvider(ABC):
    """
    LLMにリクエストを投げる基本形
    """
    @abstractmethod
    def __init__(self,AImodel,settingtext,db_url):
        """
        ここでシステムプロンプトなどの初期設定の処理をする。
        """
        self.get_content=Get_content(db_url)
        self.AImodel=AImodel
        responce=requests.get(url=f"{self.db_url}/system_prompt")
        responce.json()
        with open("conversation.json","r+",encoding="UTF-8")as f:
            data=json.load(f)
            if not data[0]["content"] == settingtext:
                data[0]["content"] =settingtext
            f.seek(0)
            json.dump(data,f,ensure_ascii=False)
            f.truncate()
    
    @abstractmethod
    async def create_comment(self,in_q:asyncio.Queue[Message],voice_q:asyncio.Queue,*out_q:asyncio.Queue[Message]):
        """
        応答を生成するためのメソッド
        voice_qには句読点ごとに区切って、またout_qには回答を丸ごと入れる
        """
        responce_comment=""
        while True:
            prompt = await in_q.get()  
            prompt_str=f"{prompt.user_name}\n{prompt.content}"
            short_memory=self.get_content.get_content(prompt.location)
            short_memory.append({"content": prompt_str, "role": "user"})
            response=await litellm.acompletion(
                model=self.model,
                messages=short_memory,
                stream=True
            )
            async for chunk in response:
                print(responce_comment+chunk.choices[0].delta.content)
                print(chunk.choices[0].delta.content or "", end="")
            


    @abstractmethod
    def create_summary(self,prompts:list):
        """
        クラスタ、配信、ユーザーの傾向などの要約作成のためのもの
        """
        message=[]
        for prompt in prompts:
            

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
      
    def _ollama_LLM_comments(self,content:str,location:str)->str:
        """
        LLMにプロンプトを入力することで回答を得る関数

        """
        #ここからLLMの処理        
        data2 =[]  
        with open("conversation.json","r",encoding="UTF-8")as f:
            data=json.load(f)
        data2=copy.deepcopy(data)
        data2.append({"role":"user","content":content}) 
        response = ollama.chat(model=self.AImodel,messages=data2)
            #resposeの構造
            #model='dsasai/llama3-elyza-jp-8b' created_at='2026-02-02T04:49:16.342579Z' done=True done_reason='stop' total_duration=23217746583 load_duration=18368811750 prompt_eval_count=47 prompt_eval_duration=4350540167 eval_count=5 eval_duration=474448249 message=Message(role='assistant', content='おはようございます', thinking=None, images=None, tool_name=None, tool_calls=None) logprobs=None
        answer = response["message"]["content"]
        data2.append({"role":"assistant","content":answer}) 
        with open("conversation.json","w",encoding="UTF-8")as f:
            f.seek(0)
            json.dump(data2,f,ensure_ascii=False)
            f.truncate()
        print(f"LLMの答え生成完了：{answer}")
        return answer

    def create_summary(self,prompt:list):
        raise NotImplementedError



