"""
全ての処理がどのような順番で処理されるかを管理するマネージャー
また、小さなAPIを投げたりそれぞれのクラスからの返り値を受け取るスクリプト
メモ:トークンで終了するようにしたい
"""
import subprocess
import sounddevice as sd
from prompt_analyze import Analyze
from unityserver import unityserver as Server
import LLM
import sound_engine
import asyncio
import httpx
from httpx import AsyncClient 
import os
from type_list import *
import Input
import traceback
import sys
    
class Booting:
    """
    起動時にやることをまとめたもの複数種類のアプリ対応に伴って変更する必要がある
    """
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

   
    async def loading(self)->Settings:
        """
        設定の読み込みを行うもの
        """
        setting=Settings.from_json("setting.jsonc")
        sd.default.device = setting.sd_default_device
        print(sd.query_devices())
        #ここで各種設定を返すようにする。
        return setting
    
    async def before_check(self,Client : AsyncClient,sound_engine_object : sound_engine.SoundProvider,input_object:Input.Input_format):
        """
        音声合成エンジンが起動できているかの確認
        """
        while not (sound_engine_object.is_ready(Client) and input_object.is_ready()):
            await asyncio.sleep(0.1)
            pass

class Output:
    """
    様々な形でoutputするただし、Unityに送る場合の処理は、new_unityserver.pyを参照
    """
    def __init__(self):
        pass
    async def soundplay(self,in_q: asyncio.Queue):
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

async def main():
    """
    ここで色々な初期設定の反映と、非同期処理の設定
    """
    Client=AsyncClient()#非同期でhttpリクエストをなげるためのもの
    booting=Booting()
    analyze=Analyze()
    server=Server()
    output=Output()
    shutdown=Shutdown()
    setting_data=await booting.loading() 
    match  setting_data.input_type:
        case "socialstream":
            inputer=Input.socialstream_input(int(input("stream_idを入力してください")))
        case "discord":
            inputer=Input.Discord_input()
        case "desktop":
            inputer=Input.Desktop_input()
        case _:
            raise ValueError("inputは現在その形式に対応していません。")
    match setting_data.LLM_Tool:
        case "ollama":
            llm=LLM.OllamaProvider(setting_data.ai_model,setting_data.setting_ai_text)
        case "vLLM":
            llm=LLM.vLLMProvider()
        case _:
            raise ValueError("LLM_Toolは,現在、ollamaとvLLM(未実装)にしか対応していません。どちらかを入力してください。")
    match setting_data.soundEngine:
        case "voicevox":
            voice=sound_engine.VOICEVOXProvider()
        case "aivis":
            voice=sound_engine.AivisProvider()
        case"coeiroink":
            voice=sound_engine.COEIROINKProvider()
        case _:
            raise ValueError("SoundEngineは現在、voicevox,aivisspeech,coerioinkにしか対応していません。いずれかを入力してください。")

    #ここ起動するソフトを動的に変えれるようにする
    if sys.platform.startswith("win"):
        await booting.Window_open_other_app(setting_data.SoundEngine_path,setting_data.socialstream_path) 
    elif sys.platform.startswith("darwin"):
        await booting.Mac_open_other_app()
    else:
        raise NotImplementedError(f"このアプリは{sys.platform}環境ではサポートされていません。")
    #await loading.Linux_open_other_app(setting_data["voicevox_path"],setting_data["socialstream_path"])
    await booting.before_check(Client,voice,inputer)

    #簡単な部分だけ型を厳密にしている
    comments_subtitle_queue=asyncio.Queue[Message](maxsize=setting_data.max_queue_size)
    comments_answer_queue=asyncio.Queue[Message](maxsize=setting_data.max_queue_size)
    comments_analyze_queue=asyncio.Queue[Message](maxsize=setting_data.max_queue_size)
    answer_analyze_queue=asyncio.Queue[Message](maxsize=setting_data.max_queue_size)
    viseme_queue=asyncio.Queue[list[list]](maxsize=setting_data.max_queue_size)
    answer_subtitle_queue=asyncio.Queue[Message](maxsize=setting_data.max_queue_size)
    au_queue=asyncio.Queue(maxsize=setting_data.max_queue_size)
    answer_voice_queue=asyncio.Queue(maxsize=setting_data.max_queue_size)
    sound_play_queue=asyncio.Queue(maxsize=setting_data.max_queue_size)

    #処理の流れ順に記述。
    worker=[
        asyncio.create_task(server.main()),
        asyncio.create_task(inputer.latest_get_comment(
            comments_answer_queue,
            comments_analyze_queue,
            comments_subtitle_queue)),
        asyncio.create_task(analyze.analyze(comments_analyze_queue)),
        asyncio.create_task(llm.create_comment(
            comments_answer_queue,
            answer_voice_queue,
            answer_analyze_queue,
            answer_subtitle_queue)),
        asyncio.create_task(analyze.analyze(answer_analyze_queue,au_queue)),
        asyncio.create_task(voice.generate_voice(
            Client,
            setting_data.speaker,
            answer_voice_queue,
            sound_play_queue,
            viseme_queue)),
        asyncio.create_task(server.send_viseme(viseme_queue)),
        asyncio.create_task(server.send_subtitle(comments_subtitle_queue,answer_subtitle_queue)),
        asyncio.create_task(server.send_au(au_queue)),
            ]
    #ここ名前を変えて要改善（余計な処理が入る感じになってしまっている。）テキストのみ、音声まで　全部でわけて考える
    if setting_data.sound_output=="Python":
        worker.append(asyncio.create_task(output.soundplay(sound_play_queue)))
    if setting_data.sound_output=="Unity":
        worker.append(asyncio.create_task(server.send_sound(sound_play_queue)))
    print("Ctrl+Cで終了します。また、エラーが出た場合強制終了します。")
    try:
        await asyncio.gather(*worker)
    
    except (KeyboardInterrupt,asyncio.CancelledError):    
        print("正常な",end="")
        if sys.platform.startswith("win"):
            shutdown.Window_shutdown()
        elif sys.platform.startswith("darwin"):
            shutdown.Mac_shutdown()
        else:
            raise NotImplementedError(f"このアプリは{sys.platform}環境ではサポートされていないはずです。")
        #この下はv0.3で使う
        """
        print("記憶整理開始")
        #この部分を変えることで、配布用かサーバー、配信用かを変える。
        print(setting_data.Stream_mode)
        if setting_data.Stream_mode:
            import stream_database_access
            memory_class=stream_database_access.Accessor(llm)
            memory_class.clustering()
            
        else:
            import user_database_access
            memory_class=user_database_access.Accessor(llm)
        """
    except httpx.ReadTimeout:
        print("接続がタイムアウトしました。パソコンのスペックが足りていないか、リクエストの数が多すぎます。")
        if sys.platform.startswith("win"):
            shutdown.Window_shutdown()
        elif sys.platform.startswith("darwin"):
            shutdown.Mac_shutdown()
        else:
            raise NotImplementedError(f"このアプリは{sys.platform}環境ではサポートされていないはずです。")

    except Exception as e:
        print(f"異常な({e})",end="")
        traceback.print_exc() 
    finally:
        print("シャットダウン")    

#エントリーポイント
if __name__=="__main__":
    asyncio.run(main())
    
