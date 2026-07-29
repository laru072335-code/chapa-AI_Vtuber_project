"""
このスクリプトは.pthファイル（AUベクトル生成モデルと感情ベクトル生成モデル）をonnx化するもの
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import torch
from transformers import AutoModelForSequenceClassification
import emotion_AI_model as AI
import onnx

def au_model_changer(path):
    """
    au_modelのonnx化のためのもの
    """
    au_model=AI.load_model(f"{path}.pth","cpu")
    au_model.eval()

    input_ids=torch.randn(1, 6)

    torch.onnx.export(
        au_model,
        input_ids,
        f"{path}.onnx",
        input_names=['emotion_vector'],
        output_names=['AU_vector'],
        dynamic_axes={
        'emotion_vector': {0: 'batch_size'},
        'AU_vector': {0: 'batch_size'}
    },
        opset_version=18,
    )

    print("感情モデルのONNX出力完了")

def emotion_ai_model_changer(model_name,file_name): 
    """
    感情ベクトル生成モデルのonnx化
    """    
    # モデルのロード（同じ要領で）
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=6
    ).float()
    model.load_state_dict(torch.load(f"{file_name}.pth", map_location="cpu"))
    model.eval()

    class ModelWithHidden(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model
        def forward(self, input_ids, attention_mask):
            outputs = self.model(
                input_ids, 
                attention_mask=attention_mask,
                output_hidden_states=True   # ← 重要！
            )
            logits = outputs.logits
            last_hidden = outputs.hidden_states[-1][:, 0, :]  # shape: (batch, seq_len, hidden_dim)
            return logits, last_hidden
        
    wrapped_model = ModelWithHidden(model)
    wrapped_model.eval()

    # ダミー入力（バッチサイズ1、最大長128など）
    dummy_input_ids = torch.randint(0, 32000, (1, 128))
    dummy_attention_mask = torch.ones(1, 128, dtype=torch.long)

    # ONNX出力の設定（logitsだけを出力）
    torch.onnx.export(
        wrapped_model,
        (dummy_input_ids, dummy_attention_mask),
        f"{file_name}.onnx",
        input_names=['input_ids', 'attention_mask'],
        output_names=['logits','hidden_states'],
        dynamic_axes={
            'input_ids': {0: 'batch_size', 1: 'sequence_length'},
            'attention_mask': {0: 'batch_size', 1: 'sequence_length'},
            'logits': {0: 'batch_size'},
            'hidden_states': {0: 'batch_size'}
        },
        opset_version=17,
        #do_constant_folding=True
    )
    """
    ここで無駄なラベルを削除している。
    """
    try:
        # 出力されたばかりのONNXファイルを読み込む
        onnx_model = onnx.load(f"{file_name}.onnx")
        fixed_count = 0

        # 全てのノードを走査し、Split演算子のバグ原因「num_outputs」を削除
        for node in onnx_model.graph.node:
            if node.op_type == "Split":
                for attr in list(node.attribute):
                    if attr.name == "num_outputs":
                        node.attribute.remove(attr)
                        fixed_count += 1

        if fixed_count > 0:
            # 上書き保存
            onnx.save(onnx_model, f"{file_name}.onnx")
            print(f"🔧 修正成功: {fixed_count}個の不整合ノードを自動クリーンアップしました。")
            print(f"🚀 これで '{f"{file_name}.onnx"}' はそのまま推論（InferenceSession）で使用可能です！")
        else:
            print("チェック完了: 修正が必要なエラーノードは見つかりませんでした。")

    except Exception as e:
        print(f"❌ 自動修正中にエラーが発生しました: {e}")
    print(f"感情モデルのONNX出力完了: {file_name}.onnx")

if __name__=="__main__":
    au_model_changer("emotionToAu_v2")
    #emotion_ai_model_changer('answerdotai/ModernBERT-base',"ModernBERT-basemodel")

