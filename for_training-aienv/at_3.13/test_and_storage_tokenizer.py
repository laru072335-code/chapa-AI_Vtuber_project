from transformers import AutoTokenizer

def storage():
    tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-base")
    tokenizer.backend_tokenizer.save("ModernBERT-base_tokenizer.json")   # JSON形式で保存

if __name__=="__main__":
    storage()
