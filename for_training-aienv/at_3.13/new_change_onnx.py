"""
embeddinggemma-2 + 感情分類ヘッドの ONNX エクスポートスクリプト
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import torch
import torch.nn as nn
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer
import onnx

DEVICE = "cpu"  # ONNXエクスポートはCPU上で行う
MODEL_NAME = "google/embeddinggemma-2"

# ===== 1. モデル定義 =====
class ExportableEmotionClassifier(nn.Module):
    def __init__(self, model_name=MODEL_NAME, num_labels=6):
        super().__init__()
        # ★ device="cpu" を明示して、MacのMPSに勝手に送られないようにする
        self.encoder = SentenceTransformer(
            model_name, 
            device="cpu", 
            model_kwargs={"torch_dtype": torch.float32}
        )
        embedding_dim = self.encoder.get_embedding_dimension()  # 768 次元
        
        hidden_dim = 512
        self.classifier = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),  # 学習時に入れた構造と完全に一致させる
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, num_labels)
        )

    def forward(self, input_ids, attention_mask):
        features = {
            "input_ids": input_ids,
            "attention_mask": attention_mask
        }
        # SentenceTransformer の順伝播 (Transformer -> Pooling -> Normalize)
        out = self.encoder(features)
        
        # 768次元・正規化済み埋め込みベクトル
        embeddings = out["sentence_embedding"]
        
        # 感情ロジット
        logits = self.classifier(embeddings)
        
        return embeddings, logits

# ===== 2. モデル初期化と学習済み重みのロード =====
export_model = ExportableEmotionClassifier(MODEL_NAME, num_labels=6)

# すべて確実に CPU 上・Float32 に統一
export_model.to(DEVICE)
export_model = export_model.float()
export_model.eval()

pth_path = "embeddinggemma-2.pth"  # Kaggleからダウンロードした重みファイル名
if os.path.exists(pth_path):
    print(f"学習済み重みをロード中: {pth_path}")
    state_dict = torch.load(pth_path, map_location=DEVICE, weights_only=True)
    export_model.load_state_dict(state_dict, strict=True)
    print("✅ 重みのロードに成功しました！")
else:
    print(f"⚠️ {pth_path} が見つかりません。")

# ===== 3. ダミー入力の準備 =====
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
dummy_text = "task: classification | query: テスト入力です"
dummy_inputs = tokenizer(dummy_text, return_tensors="pt", padding=True, truncation=True)

# ダミー入力も確実に CPU に配置
input_ids = dummy_inputs["input_ids"].to(DEVICE)
attention_mask = dummy_inputs["attention_mask"].to(DEVICE)

# ===== 4. ONNX エクスポート =====
onnx_path = "embedding_model.onnx"

torch.onnx.export(
    export_model,
    (input_ids, attention_mask),
    onnx_path,
    export_params=True,
    opset_version=18,       # ログの指示通り 18 を指定
    do_constant_folding=True,
    input_names=["input_ids", "attention_mask"],
    output_names=["embeddings", "logits"],
    dynamic_axes={
        "input_ids": {0: "batch_size", 1: "sequence_length"},
        "attention_mask": {0: "batch_size", 1: "sequence_length"},
        "embeddings": {0: "batch_size"},
        "logits": {0: "batch_size"}
    },
    dynamo=False           # ★ 超重要：TorchDynamoではなく安定したTorchScriptトレーサーを使う
)

print(f"✅ ONNXモデルの出力完了: {onnx_path}")

# ===== 5. Split ノードの不要属性クリーンアップ =====
try:
    onnx_model = onnx.load(onnx_path)
    fixed_count = 0
    for node in onnx_model.graph.node:
        if node.op_type == "Split":
            for attr in list(node.attribute):
                if attr.name == "num_outputs":
                    node.attribute.remove(attr)
                    fixed_count += 1
    if fixed_count > 0:
        onnx.save(onnx_model, onnx_path)
        print(f"🔧 {fixed_count} 個の Split 属性をクリーンアップしました。")
except Exception as e:
    print(f"クリーンアップスキップ: {e}")
