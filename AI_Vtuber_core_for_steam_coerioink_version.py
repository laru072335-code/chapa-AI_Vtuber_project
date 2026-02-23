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
before_comment=None
SPEAKER="つくよみちゃん"
SPEAKER_UUID="3c37646f-3881-5374-2a83-149267990abc"
processingAlgorithm="TD-PSOLA"
Client=httpx.AsyncClient()
def check():#voicevoxの起動チェック
    for _ in range(10):
        try:
            res = requests.get("http://localhost:50032/v1/speakers")
            if res.status_code == 200:
                return True
        except:
            pass
        time.sleep(0.1)
    return False

def loading():
    global settingAItext
    settingAItext = "あなたは、絵文字を使わずできるだけ短く返答してください。ただし、温かみを忘れないでください。\n"
    #voicevoxの起動
    #ollamaの起動
    subprocess.Popen(["ollama","serve"])
    #subprocess.run(["ollama","run","dsasai/llama3-elyza-jp-8b"])
    while not check():
        time.sleep(0.1)
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
            subprocess.run(["killall","ollama"])
            sys.exit() 
        analysis_thread = threading.Thread(target=pa.analyze_interest, args=(prompt,),daemon=True)#このコンマは消すと、動かない(args=(prompt) だと、文字列の中身が1文字ずつ引数にバラされてしまう。)
        analysis_thread.start() # バックグラウンドで処理開始
        data2 =[]
        print(prompt)    
        with open("conversation.json","r",encoding="UTF-8")as f:
            data=json.load(f)
        for d in data:    
            data2.append(d) 
        data2.append({"role":"system","content":settingAItext})
        data2.append({"role":"user","content":prompt}) 
        #ここはパソコンのスペックによって変える必要がある   
        response = ollama.chat(model="dsasai/llama3-elyza-jp-8b",messages=data2)
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
            unityserver.set_viseme_queue(viseme_result_list) 
            print(f"再生：{sentence}")
            duration=len(data)/rate
            sd.play(data,rate)
            await asyncio.sleep(0.3+(duration))
        with open("conversation.json","r+",encoding="UTF-8")as f:
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
                            "http://localhost:50032/v1/estimate_prosody",
                            json={
                                "text": answer
                                    },
                        )).json()#json関数はawait非対応
    print(sound["detail"])
    audio = (await Client.post(
                            "http://localhost:50032/v1/synthesis",
                            params={"speaker": SPEAKER},
                            json={
                                "volumeScale": 1,
                                "pitchScale": 1,
                                "intonationScale": 1,
                                "prePhonemeLength": 0,
                                "postPhonemeLength": 0,
                                "outputSamplingRate": 24000,
                                "sampledIntervalValue": 0,
                                "adjustedF0": [
                                    0
                                ],
                                "processingAlgorithm": processingAlgorithm,
                                "startTrimBuffer": 0,
                                "endTrimBuffer": 0,
                                "pauseLength": 0,
                                "pauseStartTrimBuffer": 0,
                                "pauseEndTrimBuffer": 0,
                                "speakerUuid": SPEAKER_UUID,
                                "styleId": 0,
                                "text": answer,
                                "prosodyDetail": sound["detail"],
                                "speedScale": 1
                                },
                            headers={"Content-Type": "application/json"}
                        ))
    #data, rate = sf.read(io.BytesIO(audio), dtype='float32') # dtypeを指定
    sd.play(audio,24000)
    current_time=0.0#累計時間
    for moras in sound["accent_phrases"]:
        for  mora in moras["moras"]:
            viseme=mora["vowel"].lower()
            viseme_length=mora["consonant_length"]or 0.0+mora["vowel_length"]or 0.0
            current_time += viseme_length
            viseme_result_list.append([viseme,current_time])
    return data,rate,viseme_result_list

async def main():
    while True:
        comment=await latest_get_comment()
        if not comment==None:
            await mainprocess(comment)
        await asyncio.sleep(0.1)    

if __name__=="__main__":
    unity_thread = threading.Thread(target=unityserver.entry_others,daemon=True)
    unity_thread.start() # バックグラウンドで処理開始
    loading()
    asyncio.run(main())
    asyncio.sleep(0.1)
    #while True:
        #mainprocess(latest_get_comment())

