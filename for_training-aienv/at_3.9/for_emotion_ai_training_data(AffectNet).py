"""
------
これはemotion_AIを学習させるためにAffectNetの画像からdocker上でpyfeatを使ってauベクトルを抽出し、deepfaceで取り出した感情ベクトルを.csvファイルとして保存を目的としたもの。これを感情からauを生成するaiのデータにする。
また、仮想環境も他のスクリプトで使用しているものとは異なるものを使う必要がある。(training_aienv)
------
"""
import os
import csv
import torch
import torch.nn.functional as F
import time
from deepface import DeepFace
from feat import Detector

AFFECTNET_PASS="./Affectnet"
DIRECTRY_LIST=["anger","disgust","fear","happy","sad","surprise"]
FIRST_FLAG=True#上書きを防ぐ用
USE_AU_LIST=["AU01","AU02","AU04","AU05","AU06","AU12","AU15","AU25","AU43"]
USE_HEAD_INFO=["Pitch", "Roll", "Yaw"]
USE_EMOTION_LIST=["happy","sad","surprise","angry","fear","disgust"]
"""0: joy
  1: sad
  2: surprise
  3: anger
  4: fear
  5: disgust"""
#openfaceはキー名の最初になぜか空白がある。
"""
------
この下にあるプログラムがau解析、表情分析につかったもの
------
"""

"Finish List [happy,sad,fear]"
"""DIRECTRY_LIST=["anger","disgust","fear","happy","sad","surprise"]"""

def prepare(): 
    """
    -------
    記録用ファイルの用意
    -------
    """
    detector=Detector(device="cpu")
    if FIRST_FLAG:
        with open("data.csv","w",encoding="utf-8")as f:
            writer=csv.writer(f)
            #header
            output=["img_name"]+USE_EMOTION_LIST+ USE_AU_LIST+USE_HEAD_INFO
            writer.writerow(output) 
    return detector

if __name__=="__main__": 
    #prepare
    detector=prepare()
    training_data_pass=os.path.join(AFFECTNET_PASS,"Train")
    for emotion_directry_name in os.listdir(training_data_pass):
        if emotion_directry_name in DIRECTRY_LIST:
                each_training_data_pass=os.path.join(training_data_pass,emotion_directry_name)#それぞれの感情のデータのpath
                for img_name in os.listdir(each_training_data_pass):#ここで指定されているのは、画像
                    img_path=os.path.join(each_training_data_pass,img_name)
                    if os.path.isfile(img_path):#isfileの中身は画像のpath
                        print(img_path)#画像のpath

                        result=detector.detect_image(img_path,data_type="image")   

                        judge=result.faceboxes.to_dict()
                        if float(judge["FaceScore"][0])<0.99:
                            print(judge["FaceScore"][0])
                            print("顔の確信度が低いです。")  
                        else:  
                            #au
                            au_dict=result.aus.to_dict()
                            au_list=[au_dict[a][0] for a in USE_AU_LIST ]  
                            """
                            0~5の範囲外の数字を0か5にして0~1におさめてとても小さい値は0にする処理
                            """
                            au_list = [float(x) for x in au_list]    
                            au_tensor = torch.tensor(au_list, dtype=torch.float32) 
                            au_list = au_tensor.clamp(0, 5).div(5)
                            au_tensor[au_tensor < 0.01] = 0  
                            au_list=au_tensor.tolist()        

                            time.sleep(0.3)
                           
                            #head
                            head_dict=result.poses.to_dict()
                            head_info_list=[head_dict[a][0] for a in USE_HEAD_INFO]
                            head_info_list=[float(x) for x in head_info_list]

                            #ここからdeepface
                            try:
                                result =DeepFace.analyze(img_path=os.path.abspath(img_path),actions=["emotion"])
                                result=result[0]["emotion"]
                                emotion_list=[result[e] for e in USE_EMOTION_LIST] 
                                emotion_tensor = torch.tensor(emotion_list, dtype=torch.float32)
                                emotion_tensor = F.softmax(emotion_tensor, dim=-1)#softmax関数で文章から感情ベクトルを生成するAIに合わせる。
                                emotion_tensor[emotion_tensor < 0.00001]=0#細かいの0に
                                emotion_list=emotion_tensor.tolist()   
                                with open("data.csv","a",encoding="utf-8")as f:
                                    writer=csv.writer(f)
                                    saving_list=emotion_list + au_list +head_info_list
                                    try:
                                        saving_list.insert(0,img_name)
                                    except:
                                        print("saving_listがNoneです。")    
                                        raise TypeError("stop now")
                                    writer.writerow(saving_list)
                            except:
                                print("顔が認識できませんでした。") 

                         
                            # csvファイルへの書き込み。
                            # headerは、"anger","disgust","fear","happy","sad","surprise","AU01_r", "AU02_r", "AU04_r", "AU05_r", "AU06_r", "AU07_r", "AU09_r","AU10_r", "AU12_r", "AU14_r", "AU15_r", "AU17_r", "AU20_r", "AU23_r", "AU25_r", "AU26_r", "AU45_r"   のようになっている。
                          




                    else:
                        raise TypeError(f"ファイルの構造が違います。{AFFECTNET_PASS}があっているか確認してください。") 

    """
    for dir in DIRECTRY_LIST:
            cmd=f"/build/bin/FeatureExtraction -fdir /data/{dir}"
            output=openface_container.exec_run(cmd=cmd)
            print(output)
        #test_only
    cmd=f"./build/bin/FeatureExtraction -of -fdir /data/anger -out_dir /data"#ここの/data/{file_dir}のfile_dirの部分を変えて6回繰り返してデータを集めた。
    output=openface_container.exec_run(cmd=cmd)
    print(output)

    openface_container.stop()
    openface_container.remove()
"""
"""
-----
OpenFaceの使い方メモ
docker環境にて実行
まず、一人しか写っていず、AUを抽出する今回の場合、
FeatureExtractionを使用。引数に対象のファイルを指定する。
docker run -it --rm --name openface algebr/openface:latest #これで実行準備完了

実行の仕方
buildディレクトリで、
build/bin/FaceLandmarkImg  のように実行する。
その他詳しいことは、https://github.com/TadasBaltrusaitis/OpenFace/wikiを参照。

-----
"""
