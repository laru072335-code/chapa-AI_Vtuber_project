"""
感情分析のためのファインチューニング用プログラム
SentenceTransformer (google/embeddinggemma-2) を使用
Kaggle Notebook (GPU T4) 向け修正版
"""
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torch.optim import AdamW
from sentence_transformers import SentenceTransformer
import pandas as pd
import os

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

# T4 GPU は bfloat16 に非対応のため、float16 による NaN/Inf を防ぐために float32 を明示
DTYPE = torch.bfloat16 if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else torch.float32

# ===== 1. モデル定義 =====
class EmotionClassifier(nn.Module):
    def __init__(self, model_name="google/embeddinggemma-2", num_labels=6):
        super().__init__()
        # T4環境で float16 にダウンキャストされないよう model_kwargs で dtype を明示
        self.encoder = SentenceTransformer(
            model_name,
            model_kwargs={"torch_dtype": DTYPE}
        )
        
        # google/embeddinggemma-2 の最終次元は通常 768
        embedding_dim = self.encoder.get_sentence_embedding_dimension()
        
        hidden_dim = 512
        self.classifier = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),  # 数値安定化のためにLayerNormを追加
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, num_labels)
        )

    def forward(self, inputs):
        # 埋め込みベクトルの取得
        with torch.no_grad():
            # normalize_embeddings=True でベクトルのスケールを [-1, 1] に安定化
            out = self.encoder.encode(
                inputs, 
                convert_to_tensor=True, 
                show_progress_bar=False,
                normalize_embeddings=True
            )
        
        # 分類器の型（float32）とデバイスに合わせる
        sentence_embeddings = out.to(device=self.classifier[0].weight.device, dtype=torch.float32)
        logits = self.classifier(sentence_embeddings)
        return logits

# ===== 2. データ読み込みと欠損値対策 =====
def load_wrime_data():
    # BOM対策として encoding='utf-8-sig' を指定
    cols = ["Sentence", "Writer_Joy", "Writer_Sadness", "Writer_Surprise", "Writer_Anger", "Writer_Fear", "Writer_Disgust"]
    label_cols = ["Writer_Joy", "Writer_Sadness", "Writer_Surprise", "Writer_Anger", "Writer_Fear", "Writer_Disgust"]

    df1 = pd.read_csv('/kaggle/input/datasets/ttt514614/wrimes/wrime-ver1.tsv', sep='\t', encoding='utf-8-sig')
    df2 = pd.read_csv('/kaggle/input/datasets/ttt514614/wrimes/wrime-ver2.tsv', sep='\t', encoding='utf-8-sig')

    df = pd.concat([df1[cols], df2[cols]], ignore_index=True)
    
    # 欠損値（NaN）の完全除去（これが混ざると Loss が NaN になります）
    df = df.dropna().reset_index(drop=True)
    # 文字列でないものや空文字を除去
    df = df[df["Sentence"].astype(str).str.strip() != ""].reset_index(drop=True)

    texts = df["Sentence"].tolist()
    # 0~3 のスコアを 0.0 ~ 1.0 に正規化
    labels = torch.tensor(df[label_cols].values, dtype=torch.float32) / 3.0

    return texts, labels

texts_data, labels_tensor = load_wrime_data()
print(f"有効データ件数: {len(texts_data)}")

# モデル構築
model = EmotionClassifier("google/embeddinggemma-2", num_labels=6)

# ※ 過去の壊れたチェックポイントを読み込まないよう、新規学習時はコメントアウト推奨
# if os.path.exists("/kaggle/working/model.pth"):
#     model.load_state_dict(torch.load("/kaggle/working/model.pth", map_location=DEVICE))

# ===== 3. Dataset 定義 =====
class EmotionDataset(Dataset):
    def __init__(self, texts, labels, instruction="task: classification | query: "):
        self.texts = texts
        self.labels = labels
        self.instruction = instruction

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        # 公式推奨のタスク指示子（classification）を付与
        formatted_text = f"{self.instruction}{self.texts[idx]}"
        return formatted_text, self.labels[idx]

train_dataset = EmotionDataset(texts_data[:75000], labels_tensor[:75000])
val_dataset   = EmotionDataset(texts_data[75000:], labels_tensor[75000:])

train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
val_loader   = DataLoader(val_dataset,   batch_size=64)

# ===== 4. パラメータのフリーズ =====
for param in model.parameters():
    param.requires_grad = False    

# 分類ヘッドのみ学習対象
for param in model.classifier.parameters():
    param.requires_grad = True 

trainable_params = [p for p in model.parameters() if p.requires_grad]
print(f"学習対象パラメータ数: {len(trainable_params)}")

optimizer = AdamW(trainable_params, lr=1e-4, weight_decay=1e-2)
loss_fct  = torch.nn.BCEWithLogitsLoss().to(DEVICE)

model.to(DEVICE)
model.classifier.to(torch.float32)

# ===== 5. 訓練・検証ループ =====
def train_epoch(loader):
    model.train()
    total_loss = 0
    for texts, labels in loader:
        labels = labels.to(DEVICE)
        
        optimizer.zero_grad()
        logits = model(list(texts))
        
        loss = loss_fct(logits, labels)
        
        # NaN / Inf チェック
        if torch.isnan(loss) or torch.isinf(loss):
            print("⚠️ Loss が NaN/Inf になりました。バッチをスキップします。")
            continue
            
        loss.backward()
        
        # 勾配爆発防止（Clip Grad Norm）
        torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
        
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader)

def val_epoch(loader):
    model.eval()
    total_loss = 0
    with torch.no_grad():
        for texts, labels in loader:
            labels = labels.to(DEVICE)
            logits = model(list(texts))
            loss = loss_fct(logits, labels)
            total_loss += loss.item()
    return total_loss / len(loader)

# ===== 実行 =====    
best_val_loss = float("inf")

for epoch in range(20):
    train_loss = train_epoch(train_loader)
    val_loss   = val_epoch(val_loader)
    print(f"Epoch {epoch+1:2d} | train_loss: {train_loss:.4f} | val_loss: {val_loss:.4f}")
    
    if val_loss < best_val_loss:
        best_val_loss = val_loss    
        torch.save(model.state_dict(), "/kaggle/working/model.pth")
    else:    
        print("Early stopping 条件成立")    
        break
