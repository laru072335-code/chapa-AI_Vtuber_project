import requests
import random
"""
base_url = "http://localhost:11180"

# サービス一覧取得
services = requests.get(f"{base_url}/api/services").json()
for s in services:
    print(s["id"], s["name"])

"""

"""
base_url = "http://localhost:11180"#わんコメ

service_id = "a3e074a3-85e2-43b6-aab5-827320e48245"  # 例: "626f8c47-04e4-4389-b070-bf3e60f37e38"

payload = {
    "service": {
        "id": service_id,
        "write": True,
        "speech": False,
        "persist": False
    },
    "comment": {
        "id": "unique-comment-id-2",     # 適当な一意ID
        "userId": "unique-user-id",      # 任意
        "name": "Python",                # 表示名
        "badges": [],
        "profileImage": "",
        "comment": "Hello onecomme from Python!",
        "hasGift": False,
        "isOwner": False,
        "timestamp": 0                   # 0 でも動きます
    }
}
payload1 = {
    "service": {
        "id": service_id,
        "write": True,
        "speech": False,
        "persist": False
    },
    "comment": {
        "id": "unique-comment-id-7",     # 適当な一意ID
        "userId": "unique-user-id",      # 任意
        "name": "anko",                # 表示名
        "badges": [],
        "profileImage": "",
        "comment": "exit",
        "hasGift": False,
        "isOwner": False,
        "timestamp": 0                   # 0 でも動きます
    }
}

res = requests.post(f"{base_url}/api/comments", json=payload)
time.sleep(0.5)
res1 = requests.post(f"{base_url}/api/comments", json=payload1)
#print(res.status_code)
#print(res.text)
time.sleep(0.5)
a=requests.get("http://localhost:11180/api/comments")
list=a.json()
print(list)
comments=list[0].get("data",[])
print(list[0]["data"]["comment"])
print(list[0]["data"]["name"])
print(list[1]["data"]["comment"])
print(list[1]["data"]["name"])
#print(comments)
before_comment=None"""
def comment_send(strings):
    base_url = "http://localhost:11180"#わんコメ
    service_id = "a3e074a3-85e2-43b6-aab5-827320e48245" 
    id=random.randint(0,100000)
    payloads = {
    "service": {
        "id": service_id,
        "write": True,
        "speech": False,
        "persist": False
    },
    "comment": {
        "id": f"{id}",     # 適当な一意ID
        "userId": "unique-user-id",      # 任意
        "name": f"{id}",                # 表示名
        "badges": [],
        "profileImage": "",
        "comment": strings,
        "hasGift": False,
        "isOwner": False,
        "timestamp": 0                   # 0 でも動きます
    }
                }
    requests.post(f"{base_url}/api/comments", json=payloads)
    
if __name__=="__main__":
    comment_send(input("ここにコメントを入力"))

