"""
全ての処理がどのような順番で処理されるかを管理するマネージャー
また、小さなAPIを投げたりそれぞれのクラスからの返り値を受け取るスクリプト
"""
import subprocess
import ollama
import sounddevice as sd
import json
import soundfile as sf
import io
import re
import new_prompt_analyze as analyze
from new_unityserver import unityserver as Server
import asyncio
from httpx import AsyncClient 
import websockets
import os
from dotenv import load_dotenv

class Booting:
    """起動時にやることをまとめたもの"""
    def __init__(self):
         pass
    
    async def Mac_open_other_app(self):
        """macでの起動について自動化したもの"""
        subprocess.run(["open","-a","VOICEVOX"])
        subprocess.run(['open','-a',"virtual_roid 0.2.app"])
        subprocess.run(["open","-a","socialstream"])

    async def Window_open_other_app(self,voicevox_path,socialstream_path):
        """windowsでの起動について自動化したもの"""
        os.startfile(voicevox_path)
        os.startfile("virtual Roid_0.2.exe")
        os.startfile(socialstream_path)

    async def before_check(self,Client):
        """
        -------
        voicevoxなどの音声合成エンジンの起動確認（改善予定）
        -------
        """
        for _ in range(10):
            try:
                res = await Client.get("http://localhost:50021/speakers")
                if res.status_code == 200:
                    return True
            except Exception as e:
                print(f"{e}voicevoxが起動できていません。")
            asyncio.sleep(0.3)
        return False
   
    async def loading(self):
        """
        ------
        設定の読み込みを行うもの、voicevoxの起動を待機する。
        ------
        """
        with open("setting.jsonc","r",encoding="utf-8")as f:#起動時の動作（変数データの読み込み）
            content = f.read()
            content_clean = re.sub(r'//.*', '', content)
            data = json.loads(content_clean)
            speaker =data["Speaker"]
            settingAItext=data["SettingAItext"]
            AI_model=data["AI_model"]
            max_queue_size=data["Max_queue_size"]
            sound_output=data["sound_output"]
            sd.default.device=data["sd.default.device"]
            voicevox_path=data["voicevox_path"]
            socialstream_path=data["socialstream_path"]
            print(sd.query_devices())
        print("起動しますた。")
        #ここで各種設定を返すようにする。
        return {"Speaker":speaker,"SettingAItext":settingAItext,"AImodel":AI_model,"Max_queue_size":max_queue_size,"sound_output":sound_output,"voicevox_path":voicevox_path,"socialstream_path":socialstream_path}

class Input:
    """
    ここに様々なものをシステムに流し込むための、準備をする。
    exitと入力するとシステムが終了する
    """
    def __init__(self):
        load_dotenv()
        self.session_key=os.getenv("SESSON_KEY")
    async def new_latest_get_comment(self,*out_q):
        """
        social stream に対してWebSocketによるコメント取得
        """
        uri = f"wss://io.socialstream.ninja/join/{self.session_key}/4" 

        async with websockets.connect(uri) as ws:
            print("Connected! Listening for chat messages...")
            while True:
                message = await ws.recv()
                data = json.loads(message)
                if "chatname" in data:
                    comment=data.get('chatmessage', '')
                #シャットダウンする処理
                if comment=="exit":    
                    print("シャットダウンします。")  
                    shutdown=Shutdown()    
                    shutdown.Window_shutdown()
                    raise SystemFinish()
                else:
                    for q in out_q:
                        await q.put(comment)

    async def latest_get_comment(self,Client,*out_q):
        """
        -----
        OneCommeに対してHTTPによるコメント取得(廃止済み)
        -----
        """
        previous_comments=None
        while True:
            try:
                await asyncio.sleep(0.3)  
                a= await Client.get("http://localhost:11180/api/comments?mode=diff")
                list_comment=a.json()
                if not previous_comments==list_comment[-1]["data"]["comment"]:
                    for q in out_q:
                        await q.put(list_comment[-1]["data"]["comment"])
                        previous_comments=list_comment[-1]["data"]["comment"]
            except Exception as e:
                print(f"error!{e} わんコメが起動できていません。")  

class Output:
    """
    様々な形でoutputするただし、Unityに送る場合の処理は、new_unityserver.pyを参照
    """
    def __init__(self):
        pass
    async def soundplay(self,in_q):
        """
        音声出力のためのもの
        """
        while True:
            data,rate=await in_q.get()
            sd.play(data,rate)
            sd.wait()

class Shutdown:
    """
    最後このアプリを閉じるときにすることをまとめたクラス。
    """
    def __init__(self):
        pass

    def Mac_shutdown(self):
        """macでの終了について自動化したもの"""
        subprocess.run(['osascript', '-e', 'quit app "VOICEVOX"'])
        subprocess.run(['osascript', '-e', 'quit app "virtual_roid 0.2.app"'])
        subprocess.run(["killall","ollama"])
        subprocess.run(['osascript', '-e', 'quit app "socialstream"'])

    def Window_shutdown(self):
        """windowsでの終了について自動化したもの"""
        subprocess.run(["taskkill", "/F", "/IM", "VOICEVOX.exe"], stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/F", "/IM", "virtual Roid_0.2.exe"], stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/F", "/IM", "socialstream.exe"], stderr=subprocess.DEVNULL)
    
class SystemFinish(Exception):
    """
    システムが終了する時の意図的なエラー
    """
    pass

class Workers():
    """
    システム内部の処理を表すクラス(現在は特に存在している意味なし)
    """
    def __init__(self):
        pass

class LLM(Workers):
    def __init__(self):
        super().__init__()
    """
    LLMの応答抽出についてまとめたクラス
    """
    async def ollama_LLM_comments(self,AImodel,settingtext,in_q,voice_q,*out_q):
        """
        create_taskのための関数、これは別スレッドに回すので、ここではloopを取得して本体の関数を実行
        """
        loop=asyncio.get_running_loop()
        while True:
            prompt = await in_q.get()  
            answer=await loop.run_in_executor(None,lambda:self._ollama_LLM_comments(prompt,AImodel,settingtext)) 
            #voice用にリスト化して高速化
            answers =re.split(r"(?<=[、。？！\s])",answer)
            answers = [s.strip() for s in answers if s.strip()]
            print(answers)
            works=[]
            for q in out_q:
               works.append(asyncio.create_task(q.put(answer)))
            for ans in answers:
                works.append(asyncio.create_task(voice_q.put(ans)))
            await asyncio.gather(*works)    
            
    def _ollama_LLM_comments(self,prompt,AImodel,settingtext):
        """
        LLMにプロンプトを入力することで回答を得る関数
        """
        #ここからLLMの処理        
        data2 =[]
        print(f"prompt:{prompt}")    
        with open("conversation.json","r",encoding="UTF-8")as f:
            data=json.load(f)
            if not data[0]["content"] == settingtext:
                data[0]["content"] =settingtext
            for d in data:    
                data2.append(d) 
        data2.append({"role":"user","content":prompt}) 
        response = ollama.chat(model=AImodel,messages=data2)
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

class Analyze(Workers):
    """
    プロンプトまたは、LLMの回答分析
    ここで興味推定や感情、表情生成を行う
    """
    def __init__(self):
        super().__init__()
    async def analyze(self,in_q,select_table,au=False,au_vec_q=False):
        """
        analyze.pyに分析する文章を渡して、別スレッドで実行
        """
        loop=asyncio.get_running_loop()
        while True:
            sentence=await in_q.get()
            if au:#返り値がある時だけ待つ。
                au_vec=await loop.run_in_executor(None,lambda:analyze.analyze(sentence,select_table,au))
                if au_vec_q:
                    await au_vec_q.put(au_vec)
                else:
                    raise ValueError("auがTrueの時、au_vec_qは必要です。")
                
            else:
                loop.run_in_executor(None,lambda:analyze.analyze(sentence,select_table,au))
            
class Voice(Workers):
    """
    音声を生成するクラス
    visemeも生成される
    """
    def __init__(self):
        super().__init__()
    async def voicevox_generate_voice(self,Client,speaker,in_q,sound_out_q,viseme_out_q):
        """
        音声とvisemeを生成する関数。
        voicevoxのエンジンにテキストを投げて音声データを生成する
        また、viseme_listを生成する。
        viseme_listは[[visemeの種類,経過時間],...]で記録される。
        複数一斉リクエストも検討
        """
        while True:
            answer=await in_q.get()
            viseme_result_list=[]
            sound =  (await Client.post(
                            "http://localhost:50021/audio_query",
                            params={"text": answer, "speaker": speaker}
                        )).json()#json関数はawait非対応
            audio = await Client.post(
                            "http://localhost:50021/synthesis",
                            params={"speaker": speaker},
                            content=json.dumps(sound),
                            headers={"Content-Type": "application/json"}
                        )
            data,rate = sf.read(io.BytesIO(audio.content))
            current_time=0.1#累計時間　最初の無音時間の関係で0.1秒プラスされている。
            for moras in sound["accent_phrases"]:
                for  mora in moras["moras"]:
                    viseme=mora["vowel"].lower()
                    consonaunt=mora["consonant_length"]or 0.0
                    vowel=mora["vowel_length"]or 0.0
                    viseme_length=consonaunt+vowel
                    current_time += viseme_length
                    viseme_result_list.append([viseme,current_time])
            await sound_out_q.put([data,rate])
            await viseme_out_q.put(viseme_result_list)

    async def aivis_speech_generate_voice(self,Client,speaker,in_q,sound_out_q,viseme_out_q):
        """
        音声とvisemeを生成する関数
        aivis speechを使用して音声データを生成する。
        現在実装途中
        複数一斉リクエストも検討
        """
        while True:
            answer=await in_q.get()
            viseme_result_list=[]
            sound =  (await Client.post(
                            "http://localhost:50021/audio_query",
                            params={"text": answer, "speaker": speaker}
                        )).json()#json関数はawait非対応
            audio = await Client.post(
                            "http://localhost:50021/synthesis",
                            params={"speaker": speaker},
                            content=json.dumps(sound),
                            headers={"Content-Type": "application/json"}
                        )
            data,rate = sf.read(io.BytesIO(audio.content))
            await sound_out_q.put([data,rate])
            await viseme_out_q.put(viseme_result_list)

async def main():
    """
    ここで色々な初期設定の反映と、非同期処理の設定
    """
    Client=AsyncClient()#非同期でhttpリクエストをなげるためのもの
    booting=Booting()
    llm=LLM()
    analyze=Analyze()
    voice=Voice()
    server=Server()
    input=Input()
    output=Output()
    setting_data=await booting.loading() 
    #{"Speaker":speaker,"SettingAItext":settingAItext,"AImodel":AI_model,"Max_queue_size":max_queue_size,"sound_output":sound_output,"voicevox_path":voicevox_path,"socialstream_path":socialstream_path}の辞書が帰ってくる
    """
    ここをOSによって変える
    """
    #await booting.Mac_open_other_app()
    await booting.Window_open_other_app(setting_data["voicevox_path"],setting_data["socialstream_path"])
    #await loading.Linux_open_other_app(setting_data["voicevox_path"],setting_data["socialstream_path"])
    await booting.before_check(Client)

    comments_subtitle_queue=asyncio.Queue(maxsize=setting_data["Max_queue_size"])
    comments_answer_queue=asyncio.Queue(maxsize=setting_data["Max_queue_size"])
    comments_analyze_queue=asyncio.Queue(maxsize=setting_data["Max_queue_size"])
    answer_analyze_queue=asyncio.Queue(maxsize=setting_data["Max_queue_size"])
    viseme_queue=asyncio.Queue(maxsize=setting_data["Max_queue_size"])
    answer_subtitle_queue=asyncio.Queue(maxsize=setting_data["Max_queue_size"])
    au_queue=asyncio.Queue(maxsize=setting_data["Max_queue_size"])
    answer_voice_queue=asyncio.Queue(maxsize=setting_data["Max_queue_size"])
    sound_play_queue=asyncio.Queue(maxsize=setting_data["Max_queue_size"])

    #処理の流れ順に記述。
    worker=[
        asyncio.create_task(server.main()),
        asyncio.create_task(input.new_latest_get_comment(
            comments_answer_queue,
            comments_analyze_queue,
            comments_subtitle_queue)),
        asyncio.create_task(analyze.analyze(comments_analyze_queue,"user")),
        asyncio.create_task(llm.ollama_LLM_comments(
            setting_data["AImodel"],
            setting_data["SettingAItext"],
            comments_answer_queue,
            answer_voice_queue,
            answer_analyze_queue,
            answer_subtitle_queue)),
        asyncio.create_task(analyze.analyze(answer_analyze_queue,"assistant",True,au_queue)),
        asyncio.create_task(voice.voicevox_generate_voice(
            Client,
            setting_data["Speaker"],
            answer_voice_queue,
            sound_play_queue,
            viseme_queue)),
        asyncio.create_task(server.send_viseme(viseme_queue)),
        asyncio.create_task(server.send_subtitle(comments_subtitle_queue,answer_subtitle_queue)),
        asyncio.create_task(server.send_au(au_queue)),
            ]
    if setting_data["sound_output"]=="Python":
        worker.append(asyncio.create_task(output.soundplay(sound_play_queue)))
    if setting_data["sound_output"]=="Unity":
        worker.append(asyncio.create_task(server.send_sound(sound_play_queue)))
    
    try:
        await asyncio.gather(*worker)
    
    except SystemFinish :    
        print("正常な",end="")
    except Exception as e:
        print(f"異常な({e})",end="")
    finally:
        print("シャットダウン")    

#エントリーポイント
if __name__=="__main__":
    asyncio.run(main())
    
