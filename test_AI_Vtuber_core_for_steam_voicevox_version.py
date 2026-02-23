import subprocess
import ollama
import sounddevice as sd
import time
import requests
import json
import soundfile as sf
import io
import re
import sys
import prompt_analyze as pa
import threading
import unityserver
import asyncio
import httpx
sd.default.device=2#ここは端末によって異なる
#import sounddevice as sd
#print(sd.query_devices()) 
#で確認
#blackholeの音量確認!!
#例
#0 BlackHole 2ch, Core Audio (2 in, 2 out)
#> 1 MacBook Airのマイク, Core Audio (1 in, 0 out)
#< 2 MacBook Airのスピーカー, Core Audio (0 in, 2 out)
#  3 Microsoft Teams Audio, Core Audio (1 in, 1 out)
#  4 複数出力装置, Core Audio (0 in, 2 out)
before_comment=None
Client=httpx.AsyncClient()
def check():#voicevoxの起動チェック
    for _ in range(10):
        try:
            res = requests.get("http://localhost:50021/speakers")
            if res.status_code == 200:
                return True
        except:
            print("voicevoxが起動できていません。")
        time.sleep(0.1)
    return False

def loading():
    global speaker
    global settingAItext
    settingAItext = "あなたは、絵文字を使わずできるだけ短く返答してください。ただし、温かみを忘れないでください。\n"
    #voicevoxの起動
    #container =f"voicevox"
    #subprocess.run(["podman", "rm", "-f", container], capture_output=True)
    """subprocess.Popen([
        "podman", "run", "-d", "--name", container,
        "-p", "50021:50021", "voicevox/voicevox_engine"
    ])"""#コンテナ版のみ必要
    #ollamaの起動
    subprocess.Popen(["ollama","serve"])
    #subprocess.run(["ollama","run","dsasai/llama3-elyza-jp-8b"])
    while not check():
        time.sleep(0.1)
    with open("setting.json","r+",encoding="utf-8")as f:#起動時の動作（変数データの読み込み）
        data=json.load(f)
        speaker =data["speaker"]
        f.seek(0)    
        json.dump(data,f)
        f.truncate() 
    print("起動しますた。")
    
async def latest_get_comment():
    global before_comment
    global Client
    try:
            a= await Client.get("http://localhost:11180/api/comments")
            list_comment=a.json()
            if before_comment==list_comment[-1]["data"]["comment"]:
                return None
            else:    
                before_comment=list_comment[-1]["data"]["comment"]
                return list_comment[-1]["data"]["comment"]
    except:
        print("error! わんコメが起動できていません。")        


async def mainprocess(prompt):
        if prompt=="exit":    
            print("シャットダウンします。")      
            #subprocess.run(["podman", "stop", "voicevox"])
            #subprocess.run(["podman", "rm", "voicevox"])
            subprocess.run(["killall","ollama"])
            sys.exit() 
        analysis_thread = threading.Thread(target=pa.analyze_interest, args=(prompt,),daemon=True)#このコンマは消すと、動かない(args=(prompt) だと、文字列の中身が1文字ずつ引数にバラされてしまう。)
        analysis_thread.start() # バックグラウンドで処理開始
        data2 =[]
        print(prompt)    
        with open("test_conversation.json","r",encoding="UTF-8")as f:
            data=json.load(f)
        for d in data:    
            data2.append(d) 
        data2.append({"role":"user","content":prompt}) 
        #ここはパソコンのスペックによって変える必要がある   
        response = ollama.chat(model="lfm2.5-thinking",messages=data2)
        #dsasai/llama3-elyza-jp-8b←元のモデル
        #"lfm2.5-thinking"←テスト用の軽量モデル

        #resposeの構造
        #model='dsasai/llama3-elyza-jp-8b' created_at='2026-02-02T04:49:16.342579Z' done=True done_reason='stop' total_duration=23217746583 load_duration=18368811750 prompt_eval_count=47 prompt_eval_duration=4350540167 eval_count=5 eval_duration=474448249 message=Message(role='assistant', content='おはようございます', thinking=None, images=None, tool_name=None, tool_calls=None) logprobs=None
        answer = response["message"]["content"]
        print(f"LLMの答え生成完了：{answer}")#ここからVOICEVOXの音声生成
        answers =re.split(r"[、。？！\n\t\r]+",answer)
        answers = [s.strip() for s in answers if s.strip()]
        for sentence in answers:
            data,rate,viseme_result_list=await generate_voice(sentence)
            unityserver.set_viseme_queue(viseme_result_list,sentence) 
            print(f"再生：{sentence}")
            duration=len(data)/rate
            sd.play(data,rate)
            await asyncio.sleep(0.3+(duration))
        with open("test_conversation.json","r+",encoding="UTF-8")as f:
            data =json.load(f) 
            data.append({"role":"user","content":prompt}) 
            data.append({"role":"assistant","content":answer}) 
            f.seek(0)    
            json.dump(data,f,ensure_ascii=False)#trueのほうがいいかも
            f.truncate()  
        #pa.analyze_interest(prompt)
async def  generate_voice(answer):
    global Client
    viseme_result_list=[]
    sound =  (await Client.post(
                            "http://localhost:50021/audio_query",
                            params={"text": answer, "speaker": speaker}
                        )).json()#json関数はawait非対応
    audio = await Client.post(
                            "http://localhost:50021/synthesis",
                            params={"speaker": speaker},
                            data=json.dumps(sound),
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
    return data,rate,viseme_result_list

async def main():
    while True:
        comment=await latest_get_comment()
        if not comment==None:
            await mainprocess(comment)
            """data,rate,viseme_result_list=await generate_voice(comment)
            print(f"再生：{comment}")
            duration=len(data)/rate
            sd.play(data,rate)
            await asyncio.sleep(0.3+(duration))"""#voicevox発話テスト用
        await asyncio.sleep(0.1)    

if __name__=="__main__":
    unity_thread = threading.Thread(target=unityserver.entry_others,daemon=True)
    unity_thread.start() # バックグラウンドで処理開始
    loading()
    asyncio.run(main())
    asyncio.sleep(0.1)
    #while True:
        #mainprocess(latest_get_comment())

