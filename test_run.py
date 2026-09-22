import pytest 
from unityserver import unityserver as Server
from prompt_analyze import Analyze
import asyncio
import subprocess
from sound_engine import VOICEVOXProvider as Voice
from httpx import AsyncClient 
#実装したいテスト
#コメント取得
#LLMのベンチマーク
#音声出力テスト
#実際にエントリーポイントを起動して、エラーなく通るかのテストが欲しい
#連続で音声を投げてうまくいくかのテストが欲しい
#自動でプロファイラを回す機能が欲しい

"""
pytest用のスクリプト
これで動くことを保証する
現在クラス内のすべてのメソッドに対して自動でインスタンス化してテストを行えるようにしたいと考えている。
"""

@pytest.mark.parametrize("sentence",
[
("おはよう"),
("元気？"),
("アンコール！！！")
])
#非同期式にテストに変える
@pytest.mark.asyncio
async def test_meaning_vector_and_emotion_vector(sentence):
    """
    興味推定や、意味（興味）ベクトルの生成ができているかを確認する。
    """
    analyze=Analyze()
    au_list,interest,emotion_probs=analyze._analyze(sentence,test=True)
    assert interest.shape==(768,) 
    assert emotion_probs.shape==(1,6)
    assert len(au_list)==9

@pytest.mark.parametrize("viseme,prompt,answer,au_vector",
[
  ([["o", 0.33152533173561094], ["o", 0.3985613793134689], ["e", 0.5282562024891376],["u", 0.676918862760067],["e",0.9820178434252739]],"おはよう","おはよう！",[0.5]*9),
])

@pytest.mark.asyncio
async def test_wedsocket(viseme,prompt,answer,au_vector):
    """
    エラーがなく、字幕、au、visemeが送れるかどうかを確認する。
    """
    responce_queue = asyncio.Queue()
    server=Server(responce_queue)
    server_task=asyncio.create_task(server.main(True))
    subprocess.run(['open','-a',"virtual_roid 0.2.app",'--args','--test-mode'])
    await responce_queue.get()
    #await responce_queue.get()#unityがeditモードの時のみこの部分をコメントにする。
    viseme_queue = asyncio.Queue()
    prompt_queue = asyncio.Queue()
    answer_queue= asyncio.Queue()
    au_queue = asyncio.Queue()
    await viseme_queue.put(viseme)
    await prompt_queue.put(prompt)
    await answer_queue.put(answer)
    await au_queue.put(au_vector)
    worker=[
        asyncio.create_task(server.send_viseme(viseme_queue)),
        asyncio.create_task(server.send_subtitle(prompt_queue,answer_queue)),
        asyncio.create_task(server.send_au(au_queue))
    ]
    await server_task
    # サーバーが終わったら、無限ループしているワーカーたちを強制終了する
    for task in worker:
        task.cancel()
    # キャンセル処理が完了するのを安全に待つ
    await asyncio.gather(*worker, return_exceptions=True)
    subprocess.run(['osascript', '-e', 'quit app "virtual_roid 0.2.app"'])
    assert responce_queue.empty()


@pytest.mark.parametrize("sentence",
[
("おはよう"),
("元気？"),
("アンコール！！！")
])

@pytest.mark.asyncio
async def test_generate_voice(sentence):
    """
    指定された形式でvoicevoxが音声を返してくれるかをテスト
    """
    subprocess.run(["open","-a","VOICEVOX"])
    Client=AsyncClient()
    while True:
        try:
            res = await Client.get("http://localhost:50021/speakers")
            if res.status_code == 200:
                break
        except:
           continue
        await asyncio.sleep(0.3)
    prompt_queue=asyncio.Queue()
    sound_queue=asyncio.Queue()
    viseme_queue=asyncio.Queue()
    await prompt_queue.put(sentence)
    voice=Voice()
    work=asyncio.create_task(voice.generate_voice(
        Client,
        46,
        prompt_queue,
        sound_queue,
        viseme_queue,
    ))
    output_sound=await sound_queue.get()
    output_viseme=await viseme_queue.get()
    work.cancel()
    print(output_sound)
    print(output_viseme)
    assert isinstance(output_sound, list)
    assert output_sound[1]==24000#レートの確認

    # 口パク（viseme）データの検証
    assert isinstance(output_viseme, list)
    assert len(output_viseme) > 0
    assert isinstance(output_viseme[0][0], str)
    assert isinstance(output_viseme[0][1], float)
    subprocess.run(['osascript', '-e', 'quit app "VOICEVOX"'])
    await asyncio.sleep(1)

