"""
--------
これは感情分析のためのファインチューニング用プログラムです。
SentenceTransformer (google/embeddinggemma-2) を使用
kaggle notebookにてGPU T4 *2で実行
--------
"""
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torch.optim import AdamW
from sentence_transformers import SentenceTransformer
import pandas as pd
import os

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

# EmbeddingGemma等のモデル構造に合わせたファインチューニング対象層のキーワードを指定
# （例：分類ヘッド classifier と 最終レイヤー付近）
TRAIN_LAYER_LIST = ["classifier"]  # モデルの構造に合わせて調整してください

# ===== 1. SentenceTransformer を使った分類モデルクラスの定義 =====
class EmotionClassifier(nn.Module):
    def __init__(self, model_name="google/embeddinggemma-2", num_labels=6):
        super().__init__()
        # SentenceTransformerモデルのロード
        self.encoder = SentenceTransformer(model_name)
        
        # モデルの出力次元を取得（google/embeddinggemma-2 の場合は通常 768 や 3584 などモデルサイズによる）
        embedding_dim = self.encoder.get_sentence_embedding_dimension()
        
        # 6ラベル（Joy, Sadness, Surprise, Anger, Fear, Disgust）への分類ヘッド
        hidden_dim = 512
        self.classifier = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, num_labels)
        )
    def forward(self, inputs):
        # SentenceTransformer を使用して埋め込みベクトルを取得
        # (テキストの文字列リスト、または将来的にPIL Imageのリストをそのまま渡せる)
        out = self.encoder.encode(inputs, convert_to_tensor=True, show_progress_bar=False)
        
        # 型をMLP層（float32）に合わせる
        sentence_embeddings = out.to(self.classifier[0].weight.dtype)
        
        # MLPを通す
        logits = self.classifier(sentence_embeddings)
        return logits
# データ読み込み
texts_data = pd.read_csv('/kaggle/input/datasets/ttt514614/wrimes/wrime-ver1.tsv', usecols=["Sentence"], sep='\t')
labels_data = pd.read_csv('/kaggle/input/datasets/ttt514614/wrimes/wrime-ver1.tsv', usecols=["Writer_Joy","Writer_Sadness","Writer_Surprise","Writer_Anger","Writer_Fear","Writer_Disgust"], sep='\t')
texts_data2 = pd.read_csv('/kaggle/input/datasets/ttt514614/wrimes/wrime-ver2.tsv', usecols=["Sentence"], sep='\t')
labels_data2 = pd.read_csv('/kaggle/input/datasets/ttt514614/wrimes/wrime-ver2.tsv', usecols=["Writer_Joy","Writer_Sadness","Writer_Surprise","Writer_Anger","Writer_Fear","Writer_Disgust"], sep='\t')

texts_data = pd.concat([texts_data, texts_data2])
labels_data = pd.concat([labels_data, labels_data2])
print(texts_data.shape)

texts_data = [s[0] for s in texts_data.values.tolist()]
labels_tensor = torch.tensor(labels_data.values, dtype=torch.float32) / 4.0

# モデル構築
model = EmotionClassifier("google/embeddinggemma-2", num_labels=6)

if os.path.exists("/kaggle/working/model.pth"):
    model.load_state_dict(torch.load("/kaggle/working/model.pth", map_location=DEVICE, weights_only=True))

# ===== Dataset =====
class EmotionDataset(Dataset):
    def __init__(self, texts, labels, instruction="task: clustering | query: "):
        self.texts = texts
        self.labels = labels
        self.instruction = instruction

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        # 入力テキストの頭に Instruction を付与する
        formatted_text = f"{self.instruction}{self.texts[idx]}"
        return formatted_text, self.labels[idx]

train_dataset = EmotionDataset(texts_data[:75000], labels_tensor[:75000])
val_dataset   = EmotionDataset(texts_data[75000:], labels_tensor[75000:])

train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
val_loader   = DataLoader(val_dataset,   batch_size=64)

# ===== フリーズ処理 =====
for param in model.parameters():
    param.requires_grad = False    

for name, param in model.named_parameters():
    if any(key in name for key in TRAIN_LAYER_LIST):
        param.requires_grad = True 

trainable_params = [p for p in model.parameters() if p.requires_grad]
print(f"学習対象パラメータ数: {len(trainable_params)}")

optimizer = AdamW(trainable_params, lr=1e-4)
loss_fct  = torch.nn.BCEWithLogitsLoss().to(DEVICE)

model.to(DEVICE)

# ===== 訓練・検証関数 =====
def train_epoch(loader):
    model.train()
    total_loss = 0
    for texts, labels in loader:
        labels = labels.to(DEVICE)
        
        # model に文字列リストを直接渡す
        logits = model(list(texts))
        
        loss = loss_fct(logits, labels)
        optimizer.zero_grad()
        loss.backward()
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
    print(f"Epoch {epoch+1} | train_loss: {train_loss:.4f} | val_loss: {val_loss:.4f}")
    
    if val_loss < best_val_loss:
        best_val_loss = val_loss    
        torch.save(model.state_dict(), "/kaggle/working/model.pth")
    else:    
        print("終了")    
        break
