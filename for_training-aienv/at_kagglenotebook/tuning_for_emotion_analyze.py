"""
--------
これは感情分析のためのファインチューニング用プログラムです。
とりあえず学習用にwrimeを使用
kaggle notebookにてGPU T4 *2で実行
--------
"""
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from torch.optim import AdamW  # ← PyTorch本体から読み込む
import pandas as pd
import os
DEVICE="cuda:0"
TRAIN_LAYER_LIST=["model.final_norm.weight","head","classifier","model.layer21"]

torch.device(DEVICE)


texts_data = pd.read_csv('/kaggle/input/datasets/ttt514614/wrimes/wrime-ver1.tsv', usecols=["Sentence"],sep='\t')
labels_data = pd.read_csv('/kaggle/input/datasets/ttt514614/wrimes/wrime-ver1.tsv', usecols=["Writer_Joy","Writer_Sadness","Writer_Surprise","Writer_Anger","Writer_Fear","Writer_Disgust"],sep='\t')
texts_data2 = pd.read_csv('/kaggle/input/datasets/ttt514614/wrimes/wrime-ver2.tsv', usecols=["Sentence"],sep='\t')
labels_data2 = pd.read_csv('/kaggle/input/datasets/ttt514614/wrimes/wrime-ver2.tsv', usecols=["Writer_Joy","Writer_Sadness","Writer_Surprise","Writer_Anger","Writer_Fear","Writer_Disgust"],sep='\t')
texts_data=pd.concat([texts_data,texts_data2])
labels_data=pd.concat([labels_data,labels_data2])
print(texts_data.shape)
texts_data=texts_data.values.tolist()
texts_data = [s[0] for s in texts_data]
labels_tensor = torch.tensor(labels_data.values, dtype=torch.float32)
labels_tensor=labels_tensor/4.0
model_name = 'answerdotai/ModernBERT-base'#microsoft/mdeberta-v3-base#only_japanese is ku-nlp/deberta-v3-base-japanese
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=6)
model = model.float()
if os.path.exists("/kaggle/working/model.pth"):
    model.load_state_dict(torch.load("/kaggle/working/model.pth", map_location=DEVICE, weights_only=True))

"""
# ===== 乱数でダミーデータを作成 =====
dummy_texts = [
    "今日はとても楽しかった",
    "悲しい気分だ",
    "嬉しいな",
    "怖い夢を見た",
    "驚いた",
    "最悪な一日だった",
    "幸せだ",
    "不安な気持ちがある",
] * 10  # 8文 × 10 = 80件

# ラベルは0か1のランダム（8感情分）
dummy_labels = (torch.rand(80, 8) > 0.5).float()
"""
# ===== Dataset =====
class DummyDataset(Dataset):
    def __init__(self, texts, labels):
        self.texts = texts
        self.labels = labels

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        return self.texts[idx], self.labels[idx]

# 訓練64件・検証16件に分割
#train_dataset = DummyDataset(dummy_texts[:64], dummy_labels[:64])
#val_dataset   = DummyDataset(dummy_texts[64:], dummy_labels[64:])
train_dataset = DummyDataset(texts_data[:75000], labels_tensor[:75000])
val_dataset   = DummyDataset(texts_data[75000:], labels_tensor[75000:])

train_loader = DataLoader(train_dataset, batch_size=100, shuffle=True)
val_loader   = DataLoader(val_dataset,   batch_size=100)

# ===== フリーズ =====
for param in model.parameters():
    param.requires_grad = False    
for name, param in model.named_parameters():
    if any(key in name for key in TRAIN_LAYER_LIST):
        param.requires_grad = True 

trainable_params = [p for p in model.parameters() if p.requires_grad]
print(f"学習対象パラメータ数: {len(trainable_params)}")  # デバッグ用
optimizer = AdamW(trainable_params, lr=1e-5)
loss_fct  = torch.nn.BCEWithLogitsLoss().to(DEVICE)

model.to(DEVICE)
#model = torch.nn.DataParallel(model, device_ids=[0, 1])  # 複数のGPUで実行する用のもの。しかし、保存した後の開き方について把握できていないため現在こうなっている。

# ===== 訓練・検証関数 =====
def train_epoch(loader):
    model.train()
    total_loss = 0
    for texts, labels in loader:
        inputs = tokenizer(list(texts), return_tensors='pt',
                           padding=True, truncation=True, max_length=128).to(DEVICE)
        labels=labels.to(DEVICE)
        outputs = model(**inputs)
        #エラー確認用のもの
        #print("logits:", outputs.logits)
        #print("labels:", labels)
        #print("logitsにnanあるか:", torch.isnan(outputs.logits).any())
        loss = loss_fct(outputs.logits, labels)
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
            inputs = tokenizer(list(texts), return_tensors='pt',
                               padding=True, truncation=True, max_length=128).to(DEVICE)
            labels=labels.to(DEVICE)
            outputs = model(**inputs)
            loss = loss_fct(outputs.logits, labels)
            total_loss += loss.item()
    return total_loss / len(loader)

# ===== 実行 =====    
best_val_loss=float("inf")

for epoch in range(20):
    train_loss = train_epoch(train_loader)
    val_loss   = val_epoch(val_loader)
    print(f"Epoch {epoch+1} | train_loss: {train_loss:.4f} | val_loss: {val_loss:.4f}")
        # 学習が終わったあとに呼ぶ
    if val_loss <best_val_loss:
        best_val_loss=val_loss    
        torch.save(model.state_dict(), "/kaggle/working/model.pth")
    else:    
        print("終了")    
        break
#今使用しているAIのモデルの層詳細
"""
model.embeddings.tok_embeddings.weight
model.embeddings.norm.weight
model.layers.0.attn.Wqkv.weight
model.layers.0.attn.Wo.weight
model.layers.0.mlp_norm.weight
model.layers.0.mlp.Wi.weight
model.layers.0.mlp.Wo.weight
model.layers.1.attn_norm.weight
model.layers.1.attn.Wqkv.weight
model.layers.1.attn.Wo.weight
model.layers.1.mlp_norm.weight
model.layers.1.mlp.Wi.weight
model.layers.1.mlp.Wo.weight
model.layers.2.attn_norm.weight
model.layers.2.attn.Wqkv.weight
model.layers.2.attn.Wo.weight
model.layers.2.mlp_norm.weight
model.layers.2.mlp.Wi.weight
model.layers.2.mlp.Wo.weight
model.layers.3.attn_norm.weight
model.layers.3.attn.Wqkv.weight
model.layers.3.attn.Wo.weight
model.layers.3.mlp_norm.weight
model.layers.3.mlp.Wi.weight
model.layers.3.mlp.Wo.weight
model.layers.4.attn_norm.weight
model.layers.4.attn.Wqkv.weight
model.layers.4.attn.Wo.weight
model.layers.4.mlp_norm.weight
model.layers.4.mlp.Wi.weight
model.layers.4.mlp.Wo.weight
model.layers.5.attn_norm.weight
model.layers.5.attn.Wqkv.weight
model.layers.5.attn.Wo.weight
model.layers.5.mlp_norm.weight
model.layers.5.mlp.Wi.weight
model.layers.5.mlp.Wo.weight
model.layers.6.attn_norm.weight
model.layers.6.attn.Wqkv.weight
model.layers.6.attn.Wo.weight
model.layers.6.mlp_norm.weight
model.layers.6.mlp.Wi.weight
model.layers.6.mlp.Wo.weight
model.layers.7.attn_norm.weight
model.layers.7.attn.Wqkv.weight
model.layers.7.attn.Wo.weight
model.layers.7.mlp_norm.weight
model.layers.7.mlp.Wi.weight
model.layers.7.mlp.Wo.weight
model.layers.8.attn_norm.weight
model.layers.8.attn.Wqkv.weight
model.layers.8.attn.Wo.weight
model.layers.8.mlp_norm.weight
model.layers.8.mlp.Wi.weight
model.layers.8.mlp.Wo.weight
model.layers.9.attn_norm.weight
model.layers.9.attn.Wqkv.weight
model.layers.9.attn.Wo.weight
model.layers.9.mlp_norm.weight
model.layers.9.mlp.Wi.weight
model.layers.9.mlp.Wo.weight
model.layers.10.attn_norm.weight
model.layers.10.attn.Wqkv.weight
model.layers.10.attn.Wo.weight
model.layers.10.mlp_norm.weight
model.layers.10.mlp.Wi.weight
model.layers.10.mlp.Wo.weight
model.layers.11.attn_norm.weight
model.layers.11.attn.Wqkv.weight
model.layers.11.attn.Wo.weight
model.layers.11.mlp_norm.weight
model.layers.11.mlp.Wi.weight
model.layers.11.mlp.Wo.weight
model.layers.12.attn_norm.weight
model.layers.12.attn.Wqkv.weight
model.layers.12.attn.Wo.weight
model.layers.12.mlp_norm.weight
model.layers.12.mlp.Wi.weight
model.layers.12.mlp.Wo.weight
model.layers.13.attn_norm.weight
model.layers.13.attn.Wqkv.weight
model.layers.13.attn.Wo.weight
model.layers.13.mlp_norm.weight
model.layers.13.mlp.Wi.weight
model.layers.13.mlp.Wo.weight
model.layers.14.attn_norm.weight
model.layers.14.attn.Wqkv.weight
model.layers.14.attn.Wo.weight
model.layers.14.mlp_norm.weight
model.layers.14.mlp.Wi.weight
model.layers.14.mlp.Wo.weight
model.layers.15.attn_norm.weight
model.layers.15.attn.Wqkv.weight
model.layers.15.attn.Wo.weight
model.layers.15.mlp_norm.weight
model.layers.15.mlp.Wi.weight
model.layers.15.mlp.Wo.weight
model.layers.16.attn_norm.weight
model.layers.16.attn.Wqkv.weight
model.layers.16.attn.Wo.weight
model.layers.16.mlp_norm.weight
model.layers.16.mlp.Wi.weight
model.layers.16.mlp.Wo.weight
model.layers.17.attn_norm.weight
model.layers.17.attn.Wqkv.weight
model.layers.17.attn.Wo.weight
model.layers.17.mlp_norm.weight
model.layers.17.mlp.Wi.weight
model.layers.17.mlp.Wo.weight
model.layers.18.attn_norm.weight
model.layers.18.attn.Wqkv.weight
model.layers.18.attn.Wo.weight
model.layers.18.mlp_norm.weight
model.layers.18.mlp.Wi.weight
model.layers.18.mlp.Wo.weight
model.layers.19.attn_norm.weight
model.layers.19.attn.Wqkv.weight
model.layers.19.attn.Wo.weight
model.layers.19.mlp_norm.weight
model.layers.19.mlp.Wi.weight
model.layers.19.mlp.Wo.weight
model.layers.20.attn_norm.weight
model.layers.20.attn.Wqkv.weight
model.layers.20.attn.Wo.weight
model.layers.20.mlp_norm.weight
model.layers.20.mlp.Wi.weight
model.layers.20.mlp.Wo.weight
model.layers.21.attn_norm.weight
model.layers.21.attn.Wqkv.weight
model.layers.21.attn.Wo.weight
model.layers.21.mlp_norm.weight
model.layers.21.mlp.Wi.weight
model.layers.21.mlp.Wo.weight
model.final_norm.weight
head.dense.weight
head.norm.weight
classifier.weight
classifier.bias

"""
