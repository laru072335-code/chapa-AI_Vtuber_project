"""
全ての処理がどのような順番で処理されるかを管理するマネージャー
また、小さなAPIを投げたりそれぞれのクラスからの返り値を受け取るスクリプト
メモ:トークンで終了するようにしたい
"""
import subprocess
from prompt_analyze import Analyze
import sound_engine
from new_LLM import LLMProvider
from database_utilities import Clustering
from Outputs.unityserver import unityserver 
import asyncio
import httpx
from httpx import AsyncClient 
import os
from type_list import *
import Inputs
import traceback
import sys
import psutil
import shlex

class Booting_And_Shutdown:
    """
    起動時と終了時にやることをまとめたもの
    複数種類のアプリ対応に伴って変更した
    """
    def __init__(self):
        self.soft_name_list:list[str]=[]
    
    def Mac_open_other_app(self,soft_name):
        """macでの起動について自動化したもの"""
        self.soft_name_list.append(soft_name)
        subprocess.run(["open","-a",soft_name])

    def Window_open_other_app(self,path:str):
        """windowsでの起動について自動化したもの"""
        self.soft_name_list.append(path)
        os.startfile(path)

    def Mac_shutdown(self):
        """macでの終了について自動化したもの"""
        for soft_name in self.soft_name_list:
            subprocess.run(['osascript', '-e', f'quit app "{soft_name}"'])

    def Window_shutdown(self):
        """windowsでの終了について自動化したもの"""
        for soft_name in self.soft_name_list:
            for proc in psutil.process_iter(["name", "exe"]):
                try:
                    exe_path = proc.info.get("exe")
                    if exe_path and exe_path.lower() == soft_name.lower():
                        proc.kill()  # 強制終了（taskkill /F 相当）
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

    async def loading(self)->Settings:
        """
        設定の読み込みを行うもの
        """
        setting=Settings.from_json("data/setting.jsonc")
        #ここで各種設定を返すようにする。
        return setting
    
    async def before_check(self,Client : AsyncClient,sound_engine_object : sound_engine.SoundProvider,input_object:Inputs.Input_format)->None:
        """
        音声合成エンジンが起動できているかの確認
        実行が完了すると、音声合成エンジンが起動できている
        """
        while not (await sound_engine_object.is_ready(Client) and await input_object.is_ready()):
            await asyncio.sleep(0.1)

async def main():
    """
    ここで色々な初期設定の反映と、非同期処理の設定
    """
    platform=None
    if sys.platform.startswith("win"):
        booting_and_shutdown=Booting_And_Shutdown()
        platform="win"
    elif sys.platform.startswith("darwin"):
        booting_and_shutdown=Booting_And_Shutdown()
        platform="darwin"
    else:
        raise NotImplementedError(f"このアプリは{sys.platform}環境ではサポートされていません。")
    
    setting_data=await booting_and_shutdown.loading()
    if setting_data.stream_id and (not setting_data.stream_name):
        raise ValueError("stream_nameを設定してください。")
    client_task = asyncio.to_thread(AsyncClient)
    analyze_task = asyncio.to_thread(Analyze, setting_data.DB_API, setting_data.WEB_URL,setting_data.stream_id)
    llm_task = asyncio.to_thread(LLMProvider, setting_data)
    cmd=shlex.split(setting_data.ai_start)
    process=await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=True,
    )
    # 4つの処理の完了を同時に待つ
    Client, analyze, llm = await asyncio.gather(
        client_task, analyze_task, llm_task
    )
    print(process.returncode)
    server=None
    match  setting_data.input_type:
        case "Socialstream":
            inputer=Inputs.socialstream_input(setting_data.stream_id)
            if platform=="win":
                booting_and_shutdown.Window_open_other_app(setting_data.socialstream_path)
            else:
                booting_and_shutdown.Mac_open_other_app("socialstream")
        case "Discord":
            inputer=Inputs.Discord_input()
        case "Unity":
            unity_recive_queue=asyncio.Queue(maxsize=setting_data.max_queue_size)
            server=unityserver(unity_recive_queue)
            inputer=Inputs.Unity_input(unity_recive_queue)
            if platform=="win":
                booting_and_shutdown.Window_open_other_app("virtual Roid_0.2.exe")
            else:
                booting_and_shutdown.Mac_open_other_app("UnityInput.app")
        case "Stream":
            inputer=Inputs.Stream_input(setting_data.stream_id,setting_data.Public_key)
        case _:
            raise ValueError("inputは現在その形式に対応していません。")
        
    match setting_data.soundEngine:
        case "voicevox":
            voice=sound_engine.VOICEVOXProvider()
            if platform=="win":
                booting_and_shutdown.Window_open_other_app(setting_data.SoundEngine_path)
            else:
                booting_and_shutdown.Mac_open_other_app("VOICEVOX")
        case "aivis":
            voice=sound_engine.AivisProvider()
        case"coeiroink":
            voice=sound_engine.COEIROINKProvider()
        case _:
            raise ValueError("SoundEngineは現在、voicevox,aivisspeech,coerioinkにしか対応していません。いずれかを入力してください。")

    await booting_and_shutdown.before_check(Client,voice,inputer)

    #簡単な部分だけ型を厳密にしている
    comments_subtitle_queue=asyncio.Queue[Message](maxsize=setting_data.max_queue_size)
    comments_answer_queue=asyncio.Queue[Message](maxsize=setting_data.max_queue_size)
    comments_analyze_queue=asyncio.Queue[Message](maxsize=setting_data.max_queue_size)
    answer_analyze_queue=asyncio.Queue[Message](maxsize=setting_data.max_queue_size)
    viseme_queue=asyncio.Queue[list[list]](maxsize=setting_data.max_queue_size)
    answer_subtitle_queue=asyncio.Queue[Message](maxsize=setting_data.max_queue_size)#これstr型のキューの方がいいかも
    au_queue=asyncio.Queue(maxsize=setting_data.max_queue_size)
    answer_voice_queue=asyncio.Queue(maxsize=setting_data.max_queue_size)
    sound_play_queue=asyncio.Queue(maxsize=setting_data.max_queue_size)

    #処理の流れ順に記述。
    worker=[]
    #ここ名前を変えて要改善（余計な処理が入る感じになってしまっている。）テキストのみ、音声まで　全部でわけて考える
    match setting_data.output:
        case"":
            
            worker=[

            ]
        case"Unity":
            if server==None:
                server=unityserver()
                if platform=="win":
                    booting_and_shutdown.Window_open_other_app("virtual Roid_0.2.exe")
                else:
                    booting_and_shutdown.Mac_open_other_app("UnityInput.app")
            worker=[
                asyncio.create_task(server.main()),
                asyncio.create_task(inputer.latest_get_comment(
                    comments_answer_queue,
                    comments_analyze_queue,
                    comments_subtitle_queue)),
                asyncio.create_task(analyze.analyze_and_memory(comments_analyze_queue)),
                asyncio.create_task(llm.create_comment(
                    comments_answer_queue,
                    answer_voice_queue,
                    answer_analyze_queue,
                    answer_subtitle_queue)),
                asyncio.create_task(analyze.analyze_and_memory(answer_analyze_queue,au_queue)),
                asyncio.create_task(voice.generate_voice(
                    Client,
                    setting_data.speaker,
                    answer_voice_queue,
                    sound_play_queue,
                    viseme_queue)),
                asyncio.create_task(server.send_viseme(viseme_queue)),
                asyncio.create_task(server.send_subtitle(comments_subtitle_queue,answer_subtitle_queue)),
                asyncio.create_task(server.send_au(au_queue)),
                asyncio.create_task(server.send_sound(sound_play_queue))
            ]
        case _:
            raise ValueError("outputはその方式に対応していません。音声とテキストを出力する場合、Sound、テキストのみの場合、Text、Unity(GUI)の場合、Unityに設定してください。")
    
    print("Ctrl+Cで終了します。また、エラーが出た場合強制終了します。")
    try:
        await asyncio.gather(*worker)
    
    except (KeyboardInterrupt,asyncio.CancelledError):    
        print("正常な",end="")
        clusterer=Clustering()
        if platform=="win":
            booting_and_shutdown.Window_shutdown()
        elif platform=="darwin":
            booting_and_shutdown.Mac_shutdown()
        else:
            raise NotImplementedError(f"このアプリは{sys.platform}環境ではサポートされていないはずです。")
        for t in worker:
            if not t.done():
                t.cancel()
        print("記憶整理開始")
        if setting_data.stream_id:
            clusterer.stream_clustering(llm,setting_data.stream_id,setting_data.stream_name)
        else:
            clusterer.user_clustering(llm,setting_data.DB_API,setting_data.WEB_URL)
        cmd=shlex.split(setting_data.ai_stop)
        process=await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )

    except httpx.ReadTimeout:
        print("接続がタイムアウトしました。パソコンのスペックが足りていないか、リクエストの数が多すぎます。")
        if sys.platform.startswith("win"):
            booting_and_shutdown.Window_shutdown()
        elif sys.platform.startswith("darwin"):
            booting_and_shutdown.Mac_shutdown()
        else:
            raise NotImplementedError(f"このアプリは{sys.platform}環境ではサポートされていないはずです。")
        cmd=shlex.split(setting_data.ai_stop)
        process=await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )

    except Exception as e:
        print(f"異常なエラー({e})",end="")
        traceback.print_exc() 
    finally:
        for t in worker:
            if not t.done():
                t.cancel()
        print("シャットダウン")    

#エントリーポイント
if __name__=="__main__":
    asyncio.run(main())
    
