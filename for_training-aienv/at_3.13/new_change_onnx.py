import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel
DEVICE = "cpu"  # ONNX変換はCPU上で行うのが安全で確実です

# ===== 1. ONNX化用に調整したモデルクラスの定義 =====
# SentenceTransformerではなく、Hugging FaceのAutoModelをベースに直接テンソルを受ける構造にします
class ExportableEmotionClassifier(nn.Module):
    def __init__(self, model_name="google/embeddinggemma-2", num_labels=6):
        super().__init__()
        # 埋め込み用バックボーンモデル
        self.backbone = AutoModel.from_pretrained(model_name)
        
        # 自作の分類ヘッド
        embedding_dim = getattr(self.backbone.config, "hidden_dim", getattr(self.backbone.config, "hidden_size", 768))
        hidden_dim = 512
        self.classifier = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, num_labels)
        )

    def forward(self, input_ids, attention_mask):
        # 1. バックボーンを通して隠れ状態を取得
        outputs = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        
        # 2. 平均プーリング（Mean Pooling）で文埋め込みベクトル（意味ベクトル）を算出
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(outputs.last_hidden_state.size()).float()
        sum_embeddings = torch.sum(outputs.last_hidden_state * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        embeddings = sum_embeddings / sum_mask

        # 3. 分類ヘッドを通して感情ロジットを算出
        sentence_embeddings = embeddings.to(self.classifier[0].weight.dtype)
        logits = self.classifier(sentence_embeddings)

        # ★ 意味ベクトル（embeddings）と感情スコア（logits）を両方返す
        return embeddings, logits

# ===== 2. モデルの初期化と学習済み重みのロード =====
model_name = "google/embeddinggemma-2"
export_model = ExportableEmotionClassifier(model_name, num_labels=6)

# 保存された.pthをロード（キー名の不一致に対応するためstrict=Falseにするか、classifierのみロード）
state_dict = torch.load("embeddinggemma-2.pth", map_location=DEVICE)
export_model.load_state_dict(state_dict, strict=False)

# ★ ここが超重要：モデル全体の型を FP32 (float) に揃え、評価モードにする
export_model = export_model.float()
export_model.eval()

# ===== 3. ダミー入力の準備 =====
tokenizer = AutoTokenizer.from_pretrained(model_name)
dummy_text = "task: clustering | input: テスト入力です"
dummy_inputs = tokenizer(dummy_text, return_tensors="pt", padding=True, truncation=True)

# ===== 4. ONNX化の実行 =====
onnx_path = "embedding_model.onnx"

torch.onnx.export(
    export_model,
    (dummy_inputs["input_ids"], dummy_inputs["attention_mask"]),
    onnx_path,
    export_params=True,
    opset_version=18,
    do_constant_folding=True,
    input_names=["input_ids", "attention_mask"],
    output_names=["embeddings", "logits"],
    dynamic_axes={
        "input_ids": {0: "batch_size", 1: "sequence_length"},
        "attention_mask": {0: "batch_size", 1: "sequence_length"},
        "embeddings": {0: "batch_size"},
        "logits": {0: "batch_size"}
    },
)

print(f"ONNXモデルの出力完了: {onnx_path}")
