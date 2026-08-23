"""
感情ベクトル(6次元) -> AUベクトル(14次元) 変換モデル

感情次元:
  0: joy
  1: sad
  2: surprise
  3: anger
  4: fear
  5: disgust

AU次元(将来は左右で分けたい。)
  0:au01 (絶対いる)
  1:au02 (絶対いる)
  2:au04 (絶対いる)
  3:au05 (絶対いる)
  4:au06 (絶対いる)
  au 07 09 10 11 はいらない
  5:au12 (絶対いる)
  au14はいらない
  6:au15 (絶対いる)
  au17,20,23,
  7:au25(多分いる)
  au 28,はいらない
  8:au43 (あって損なし)
  9:Pitch
  10:Roll
  11:Yaw

  USE_AU_LABEL_LIST=["au01","au02","au04","au05","au06","au12","au15","au43"]
  (ここから頭の角度)
  USE_HEAD_INFO=["Pitch", "Roll", "Yaw"]

// これは将来の設計
{AU次元 (左右ペア):
  0:  AU1_L   1:  AU1_R
  2:  AU2_L   3:  AU2_R
  4:  AU4_L   5:  AU4_R
  6:  AU5_L   7:  AU5_R
  8:  AU6_L   9:  AU6_R
  10: AU12_L  11: AU12_R
  12: AU15_L  13: AU15_R}

  これはkaggle notebookにおいて実行された。(GPU T4)
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import pandas
import torch.optim as optim

EMOTION_DIM = 6
AU_DIM = 9
HIDDEN=256
BATCH=200
DEVICE="mps"
LR=0.001
EPOCHES=500

EMOTION_LABELS =["happy","sad","surprise","angry","fear","disgust"]
BORDER_AU_OR_HEAD=9
AU_LABELS = ["AU01","AU02","AU04","AU05","AU06","AU12","AU15","AU25","AU43",]
#これら三つはどうする？"Pitch", "Roll", "Yaw"

class EmotionToAUModel(nn.Module):
    """
    感情ベクトル -> AUベクトル の MLP モデル
    出力は 0~1 (各AUの活性度)
    """
    def __init__(self, input_dim=EMOTION_DIM, hidden=HIDDEN, output_dim=AU_DIM):
        super().__init__()
 
        self.fc_in = nn.Linear(input_dim, hidden)  # 中間ベクトルへの次元拡張
        self.ln    = nn.LayerNorm(hidden)           # 層正規化
 
        # 2つの残差ブロック（特徴をより学習しやすい形に整理）
        self.res1 = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.GELU(),               # 活性化関数
            nn.Linear(hidden, hidden)
        )
        self.res2 = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.GELU(),
            nn.Linear(hidden, hidden)
        )
 
        self.head = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.GELU(),
            nn.Linear(hidden, output_dim),

        )
 
    def forward(self, x):
        x = self.fc_in(x)
        x = self.ln(x)
        x = x + self.res1(x)  # 残差接続
        x = x + self.res2(x)  # 残差接続
        raw=self.head(x)
        au_part  = torch.sigmoid(raw[:, :BORDER_AU_OR_HEAD])   
        #head_part  = raw[:, BORDER_AU_OR_HEAD:]                  
        return au_part
class  EmotionAUDataset(Dataset):
    def __init__(self, emotions, au_labels):
        self.emotions = torch.tensor(emotions.values,dtype=torch.float32)
        self.au_labels = torch.tensor(au_labels.values,dtype=torch.float32)

    def __len__(self):
        return len(self.emotions)

    def __getitem__(self, idx):
        return self.emotions[idx], self.au_labels[idx]
    
def loader(csv_path):
    data=pandas.read_csv(csv_path,sep=',')
    data = data.dropna()
    emotions=data[EMOTION_LABELS]
    au_labels=data[AU_LABELS]
    splite_value=int(len(emotions)*0.95)
    train_data=EmotionAUDataset(emotions[:splite_value],au_labels[:splite_value])
    val_data=EmotionAUDataset(emotions[splite_value:],au_labels[splite_value:])
    train_loader=DataLoader(train_data,batch_size=BATCH,shuffle=True)
    val_loader=DataLoader(val_data,batch_size=BATCH,shuffle=False)
    return train_loader,val_loader

def train(csv_path,save_path,patience=50):
    train_loader,val_loader=loader(csv_path)
    model     = EmotionToAUModel().to(DEVICE)
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=20, factor=0.5)
    best_val_loss  = float("inf")
    no_improve=0

    for epoch in range(1, EPOCHES + 1):
        # --- 学習 ---
        
        model.train()
        train_loss = 0.0
        for emotion, au in train_loader:
            emotion, au = emotion.to(DEVICE), au.to(DEVICE)
            optimizer.zero_grad()
            pred = model(emotion)
            loss = criterion(pred, au)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        # --- 検証 ---
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for emotion, au in val_loader:
                emotion, au = emotion.to(DEVICE), au.to(DEVICE)
                pred = model(emotion)
                val_loss += criterion(pred, au).item()
        val_loss /= len(val_loader)

        scheduler.step(val_loss)

        if epoch % 50 == 0 or epoch == 1:
            print(f"Epoch {epoch:4d}/{EPOCHES}  train={train_loss:.5f}  val={val_loss:.5f}")

        # --- Early stopping & ベスト保存 ---
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            no_improve    = 0
            torch.save(model.state_dict(), save_path)
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"[train] Early stopping at epoch {epoch} (best val={best_val_loss:.5f})")
                break

    print(f"[train] 完了 - ベストモデル保存: {save_path}  (val_loss={best_val_loss:.5f})")


    print(f"[train] 完了 - ベストモデル保存: {save_path}  (val_loss={best_val_loss:.5f})")

def load_model(path: str,device) -> EmotionToAUModel:
    """
    ------
    モデルをloadする。
    ------
    """
    model = EmotionToAUModel()
    model.load_state_dict(torch.load(path, map_location=torch.device(device)))
    model.eval()
    return model

def predict(model,emotion_vec: list[float], device: str = "cpu") -> list[float]:
    """
    ------
    モデルをつかって推論をする。
    ------
    """
    emotion_vec=torch.tensor(emotion_vec).to(device)
    x = torch.tensor(emotion_vec, dtype=torch.float32).unsqueeze(0).to(device)
    with torch.no_grad():
        out = model(x)
    out=torch.sigmoid(out)    
    return out.squeeze(0).tolist()

if __name__=="__main__":
      train("/kaggle/input/datasets/ttt514614/training-data/data.csv","/kaggle/working/emotionToAu.pth")
