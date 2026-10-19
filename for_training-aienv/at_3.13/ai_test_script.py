"""
-----
ここで、様々なAIの性能テストを実施する。ただし、ベンチマークテストをする機能はない。
-----
"""
from transformers import AutoTokenizer,AutoModelForSequenceClassification
import torch
import emotion_AI_model as AI
def test_old():
    tokenizer = AutoTokenizer.from_pretrained('ku-nlp/deberta-v3-base-japanese')
    model = AutoModelForSequenceClassification.from_pretrained('ku-nlp/deberta-v3-base-japanese',num_labels=6)
    model = model.float()
    model.load_state_dict(torch.load("only_japanese_expression_vector_model.pth",map_location=torch.device("mps")))#ここのdeviceは環境によって臨機応変にかえる。
    model.eval()

    au_model=AI.load_model("emotionToAu.pth","cpu")

def analyze(sentence,mode="both"):
    """
    ------------
    これでユーザーのプロンプトや、sentenceの感情分析と興味推定を行えます。
    ------------
    """
    tokenize = tokenizer(sentence, return_tensors='pt')
    with torch.no_grad():
        outputs = model(**tokenize,output_hidden_states=True)
    if mode=="both" or mode=="interest":
        interest_vector = outputs.hidden_states[-1]
        print(interest_vector.shape)
    if mode=="both" or mode=="expression":
        emotion_logits = outputs.logits.squeeze()
        emotion_vector = torch.softmax(emotion_logits,dim=0).numpy()
        print(emotion_vector)
    #return emotion_vector    
def test_onnx():
    import onnxruntime as ort
    import numpy as np

    try:
        session = ort.InferenceSession("embedding_model.onnx")
        print("✅ ONNXモデルの読み込みに成功しました！")
        
        # ダミー入力で実行テスト
        dummy_ids = np.ones((1, 10), dtype=np.int64)
        dummy_mask = np.ones((1, 10), dtype=np.int64)
        
        outputs = session.run(None, {"input_ids": dummy_ids, "attention_mask": dummy_mask})
        print("出力1（embeddings）形状:", outputs[0].shape)
        print("出力2（logits）形状:", outputs[1].shape)
    except Exception as e:
        print("❌ 読み込み失敗:", e)

if __name__=="__main__":
    while True:
        test_onnx()
        #emotion_vector=analyze(input("文を入力してください。"),"interest")    
        #au_list=AI.predict(au_model,emotion_vector,)    
        #print(emotion_vector)

       
