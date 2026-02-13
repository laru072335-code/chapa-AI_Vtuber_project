import json
from datetime import date
import search_genre 
import Synchronizationdictionary as Syn
import googleapiclient.discovery
from dotenv import load_dotenv
import os 
import time
import torch
import fugashi
from contextlib import contextmanager
import unidic_lite
#import emotion_AI as AI
# OMP_NUM_THREADSとMKL_NUM_THREADSが設定されているか確認
print(f"OMP_NUM_THREADS: {os.environ.get('OMP_NUM_THREADS')}")
print(f"MKL_NUM_THREADS: {os.environ.get('MKL_NUM_THREADS')}")
# 読み込み
stopword =["こと","もの","とき","ところ","ひと","自分","問題","考え","気持ち","理由","方法","目的","場合","結果","変化","状態","事実","意味","内容","関係","程度","種類","全体","一部","一般","違い","能力","効果","役割","印象","可能性","必要","習慣","基本","中心","対象","原則","これ","それ","あれ","ここ","そこ","あそこ","日","月","年","今日","明日","昨日","時間","午前","午後","今","前","後","中","数","回","分","度","現在","過去","未来","最初","最後","単位","量","率","ゼロ","一番","上","下","右","左","前","後ろ","外","内","場所","方","家","道","横","隅","奥","側","体","手","目","口","頭","生活","仕事","お金","食事","水","空気","声","名前","年齢","社会","国","会社","店","駅","会議","システム","サービス","ニュース","原因","規則","決定","計画","活動","経験","意見","光","音","色","味","匂い","温度","力","形","天","地","風","雨","雪","文","話","言葉","文字","質問","答え","説明","表現","逆","等身","枚数","出身","目標","様子","人","時","ため","内容","分野","部門","企業","概要","今回","日","土曜","今日","最近","年代","世紀","年","last","邦題","名義","名称","主人","ひとり","二人","少年","両親","子孫","一人","おなか","サイト","雑貨","作品","登場","提供","原料","添加","語","並","使い","元気","今","暇","話題","タイトル"]#汎用性の高すぎる名詞
check= False
tagger =None
load_dotenv('.env')
depth=0
device = torch.device("mps") 
service = googleapiclient.discovery.build("customsearch", "v1", developerKey=os.getenv('SEARCH_API_KEY'))#検索のモデル定義
# M4 Macでのセグメンテーション違反対策としてスレッド数を1に制限
@contextmanager
def envsetting(dic):#辞書形式で渡す
    print(dic)
    default_key={}
    for option,value in dic.items():
        default_key[option] =os.environ.get(option)
        os.environ[option]=value
        print("設定変更")
    print(default_key)
    print(f"OMP_NUM_THREADS: {os.environ.get('OMP_NUM_THREADS')}")
    print(f"MKL_NUM_THREADS: {os.environ.get('MKL_NUM_THREADS')}")
    try:
        yield
    finally:
        for option in dic:
            if default_key[option] is None:
                del os.environ[option]
            else:    
                os.environ[option]=default_key[option]
            print("元に戻す")   


def analyze_interest(prompt,depth=0):
    #ここから、名刺抽出
    global stopword
    global check
    global tagger
    bigkey=" "
    smallkey =" "#この二つ初期化
    depth = int(depth)+1
    if depth == 3:#深度制限
        print("深度が上限に達しました。")
        return 
    if not check :
        tagger = fugashi.Tagger('-d "{}"'.format(unidic_lite.DICDIR))
        check =True
    nodes = tagger(prompt)
    nouns = []#一般の名詞
    proper_nouns=[]#固有名詞
    for node in nodes:
        if node.feature.pos1 == '名詞' and (node.feature.pos2=='普通名詞' or node.feature.pos2=='サ変名詞'):#一般の名詞
            if node.surface not in stopword:
                nouns.append(node.surface)
        if node.feature.pos1 =='名詞' and node.feature.pos2 == '固有名詞':#固有名詞
            proper_nouns.append(node.surface)

        print(node.surface)  
    print("品詞分解オッケー")
        #ここから、興味に分類
    with open("machine_dictionary.json","r",encoding="UTF-8")as f1,open("interest.json","r+",encoding="UTF-8") as f2:
        data1 =json.load(f1)
        data2 = json.load(f2)
        print(nouns)
        print(proper_nouns)
        for noun in nouns: 
            print(noun)
            if noun in data1:
                bigkey =data1[noun][0]
                smallkey = data1[noun][1]
            else:
                print("beta")#辞書にない単語をどうする
                (bigkey,smallkey)=search_genre.unknown_word_classification(noun)
                Syn.synchronize(bigkey,smallkey,noun)#新しい単語を分類して辞書に追加
        context=" "#初期化
        with envsetting({"KMP_DUPLICATE_LIB_OK":"TRUE"}):
            for proper_noun in proper_nouns: #ここに固有名詞の処理
                    if proper_noun in data1:#重複検索回避
                        bigkey =data1[proper_noun][0]
                        smallkey = data1[proper_noun][1]
                    else:    
                        print("search")
                        result = service.cse().list(
                            q=proper_noun+"とは？",     # 検索クエリ（固有名詞）
                            cx=os.getenv('SEARCH_ENGINE'),   # カスタム検索エンジンID
                            num=5       # 取得する結果の数
                            ).execute()
                        time.sleep(0.1)#HTTPエラー防止
                        for r in result["items"]:
                            context += r["snippet"]
                        analyze_interest(context,depth)

        if bigkey in data2 :
            data2[bigkey]["value"] += 1
        else:
            data2[bigkey]={}
            data2[bigkey]["value"] = 1
            data2[bigkey]["date"]= str(date.today())
        if smallkey in data2 :
            data2[smallkey]["value"] += 1
        else:
            data2[smallkey]={}
            data2[smallkey]["value"] = 1
            data2[smallkey]["date"]= str(date.today())

        f2.seek(0)  # ファイルの先頭に戻る
        json.dump(data2, f2, ensure_ascii=False)
        f2.truncate()  # 余分なデータを削除  
    
if  __name__ =="__main__":
    analyze_interest(input("文章入力"))
    #analyze_viseme(input("文章入力"))
