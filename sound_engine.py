"""
音声合成エンジンにリクエストを投げたり、visemeデータを生成するもの
"""
from abc import ABC, abstractmethod
from httpx import AsyncClient
import soundfile as sf
import io
import json
import asyncio
class SoundProvider(ABC):
    """
    音声を生成するための基本形
    """
    @abstractmethod
    async def generate_voice(self,Client:AsyncClient,speaker,in_q:asyncio.Queue,sound_out_q:asyncio.Queue,viseme_out_q:asyncio.Queue[list[list]]):
        pass
    @abstractmethod
    async def is_ready(self,Client:AsyncClient)->bool:
        pass

class VOICEVOXProvider(SoundProvider):
    """
    voicevoxで音声を生成するクラス
    visemeも生成される
    """
    async def generate_voice(self,Client:AsyncClient,speaker:int ,in_q:asyncio.Queue,sound_out_q:asyncio.Queue,viseme_out_q:asyncio.Queue[list[list]]): 
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
    
    async def is_ready(self, Client:AsyncClient):
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
            await asyncio.sleep(0.3)
        return False

class AivisProvider(SoundProvider):
    """
    aivisspeechで音声を生成するクラス(現在未実装)
    """
    async def generate_voice(self,Client:AsyncClient,speaker,in_q:asyncio.Queue,sound_out_q:asyncio.Queue,viseme_out_q:asyncio.Queue[list[list]]):
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

    async def is_ready(self,Client:AsyncClient)->bool:
           pass

class COEIROINKProvider(SoundProvider):
    """
    COEIROINKで音声を生成するクラス(未実装)
    """
    async def is_ready(self,Client:AsyncClient)->bool:
            pass

    async def generate_voice(self, Client: AsyncClient, speaker, in_q: asyncio.Queue, sound_out_q: asyncio.Queue, viseme_out_q: asyncio.Queue):
        raise NotImplementedError

