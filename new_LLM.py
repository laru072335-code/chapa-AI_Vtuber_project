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
#from Tool import Tools

class LLMProvider():
    """
    LLMにリクエストを投げる基本形
    tool callingするとき、温度が高いと厄介かも
    """
    def __init__(self,setting:Settings,stream_id:int):
        """
        ここでシステムプロンプトなどの初期設定の処理をする。
        ここでインターネットに繋がっているかの判定するための関数が欲しい
        """
        self.get_content=Get_content(setting.DB_API,setting.WEB_URL)
        self.AImodel=setting.AImodel

        with open("data/system_prompt.md","r+",encoding="utf-8")as f:
            prompt=f.read()
            f.seek(0)
            f.truncate()

            if internet_access():
                responce=requests.get(url=f"{setting.db_url}/system_prompt")
                internet_prompt=responce.json()
                if not (internet_prompt==prompt):
                    print(f"システムプロンプト{prompt}")
                    f.write(prompt)
                
            else:
                print("警告！！　システムプロンプトを取得できませんでした。ネットの接続を確認してください。")
                print("存在すれば、オフラインに保存されているシステムプロンプトを使用します。")

        self.prompt=prompt
        self.get_content.get_user_profile()
        #tool=Tools(setting,stream_id)
        #self.TOOLS, self.AVAILABLE_FUNCTIONS=tool.tools()

    
    async def create_comment(self,in_q:asyncio.Queue[Message],voice_q:asyncio.Queue,*out_q:asyncio.Queue[Message]):
        """
        応答を生成するためのメソッド
        voice_qには句読点ごとに区切って、またout_qには回答を丸ごと入れる
        """
        #responce_comment=""
        comment_list=[

        ]
        while True:
            comment_list=[
                {
                    "content":[
                    {"type":"text","text":self.prompt}],
                    "role":"system"
                }
            ]
            prompt = await in_q.get()  
            comments=self.get_content.get_content(prompt.authority)

            for comment in comments:
                if comment.role==role_type.user:
                    comment_list.append({"content":[
                    {"type":"text","text":prompt.user_name},
                    {"type":"text","text":comment.text}
                    ],
                    "role":"user"})
                elif comment.role==role_type.assistant:
                    comment_list.append({"content":[
                    {"type":"text","text":comment.text}
                    ],
                    "role":"assistant"})
                else:
                    raise ValueError(f"commentに想定されていないロール{comment.role}が入っています。")
            comment_list.append({"content":[
                {"type":"text","text":prompt.user_name},
                {"type":"text","text":prompt.content}
                ],
                "role":"user"})
            response=await litellm.acompletion(
                model=self.AImodel,
                messages=comment_list,
                tool_choice="auto",
                tools=self.TOOLS,
                #stream=True
            )
            works=[]
            answer=response.choices[0].message.content
            answers =re.split(r"(?<=[、。？！\s])",answer)
            for q in out_q:
                works.append(asyncio.create_task(q.put(Message(user_name="assistant",content=answer,type=prompt.type,authority=prompt.authority,detail=prompt.detail))))
            for ans in answers:
                works.append(asyncio.create_task(voice_q.put(ans)))
            await asyncio.gather(*works)    
            


    async def create_summary(self,prompts:list[str]):
        """
        クラスタ、配信、ユーザーの傾向などの要約作成のためのもの
        テキストのリストを渡す
        """
        message_list=[]
        for prompt in prompts:
            message_list.append({"content":prompt, "role": "user"})
        message_list.append({"content":"これらの内容を要約して、400字以内にまとめてください。","role":"system"})
        response = await litellm.acompletion(
                    model=self.AImodel, 
                    messages=message_list, 
                    #stream=True
                )
        return response.choices[0].message.content
