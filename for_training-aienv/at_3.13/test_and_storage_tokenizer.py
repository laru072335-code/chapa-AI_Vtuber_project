# 開発側で1回だけ（ネットあり）
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer
import os
def storage_2():
    snapshot_download("google/embeddinggemma-2", local_dir="embeddinggemma-2")
def test():
    os.environ["HF_HUB_OFFLINE"] = "1"  # importより前に設定
    model = SentenceTransformer(
        "./models/embeddinggemma-2",
        config_kwargs={"vision_config": None, "audio_config": None},
    )
def test_2():
    OFFLINE_PATH="embeddinggemma-2"
    ONLINE_PATH="google/embeddinggemma-2"
    model = SentenceTransformer(OFFLINE_PATH)

    query = "What causes the northern lights?"
    document = "The northern lights are caused by charged particles from the sun."

    query_emb = model.encode(query, prompt_name="SearchQuery")
    doc_emb = model.encode(document, prompt_name="Document")
    print(model.similarity(query_emb, doc_emb))
    #model.save("embeddinggemma-2")


from transformers import AutoTokenizer

def storage():
    tokenizer = AutoTokenizer.from_pretrained("google/embeddinggemma-2")
    tokenizer.backend_tokenizer.save("embeddinggemma-2.json")   # JSON形式で保存

if __name__=="__main__":
    storage()


# アプリ側（配布物に ./models を含める）


