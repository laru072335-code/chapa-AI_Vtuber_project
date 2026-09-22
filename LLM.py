"""
LLMにリクエストを投げるためのファイル
"""
from abc import ABC, abstractmethod
import ollama
import json
import asyncio
import re
from type_list import *
import copy

class LLMProvider(ABC):
    """
    LLMにリクエストを投げる基本形
    """
    @abstractmethod
    def __init__(self):
        """
        ここでシステムプロンプトなどの初期設定の処理をする。
        """
        pass
    @abstractmethod
    async def create_comment(self,in_q:asyncio.Queue[Message],voice_q:asyncio.Queue,*out_q:asyncio.Queue[Message]):
        """
        応答を生成するためのメソッド
        voice_qには句読点ごとに区切って、またout_qには回答を丸ごと入れる
        """
        pass

    @abstractmethod
    def create_summary(self,prompt:list):
        """
        クラスタ、配信、ユーザーの傾向などの要約作成のためのもの
        """
        pass

class OllamaProvider(LLMProvider):
    """
    Ollamaでリクエストを投げるためのもの
    """
    def __init__(self,AImodel:str,settingtext:str):
        self.AImodel=AImodel
        with open("conversation.json","r+",encoding="UTF-8")as f:
            data=json.load(f)
            if not data[0]["content"] == settingtext:
                data[0]["content"] =settingtext
            f.seek(0)
            json.dump(data,f,ensure_ascii=False)
            f.truncate()

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
      
    def _ollama_LLM_comments(self,prompt:str)->str:
        """
        LLMにプロンプトを入力することで回答を得る関数
        """
        #ここからLLMの処理        
        data2 =[]  
        with open("conversation.json","r",encoding="UTF-8")as f:
            data=json.load(f)
        data2=copy.deepcopy(data)
        data2.append({"role":"user","content":prompt}) 
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


class vLLMProvider(LLMProvider):
    """
    実装予定
    """
    async def create_comment(self,in_q:asyncio.Queue[Message],voice_q:asyncio.Queue,*out_q:asyncio.Queue[Message]):
        print("現在未実装")

    def create_summary(self,prompt:list):
        raise NotImplementedError

    def __init__(self):
        raise NotImplementedError



