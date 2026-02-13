import json
def synchronize(bigkey,smallkey,newword):#辞書更新時にこれを実行
     
     with open("categories.json","r+",encoding="UTF-8")as f1,open("machine_dictionary.json","r+",encoding="UTF-8")as f2:
        data1 = json.load(f1)
        data2 = json.load(f2)
        print(bigkey)
        print(smallkey)
        print(newword)
        data1[bigkey][smallkey].append(newword)
        data1["extradata"]["unknown_word"].append(newword)
        data2[newword]=[bigkey,smallkey]
        f1.seek(0)    
        json.dump(data1,f1,ensure_ascii=False)
        f1.truncate()  
        f2.seek(0)    
        json.dump(data2,f2,ensure_ascii=False)
        f2.truncate()  
    
def firstsynchronize():#最初にこれを実行
    with open("categories.json","r",encoding="UTF-8")as f1,open("machine_dictionary.json","w",encoding="UTF-8")as f2:
        data1 = json.load(f1)
        data2 = {}
        for bigkey,value in data1.items():
            for smallkey,words in value.items():
                for word in words:
                    data2[word]=[bigkey,smallkey]
        f2.seek(0)    
        json.dump(data2,f2,ensure_ascii=False)
        f2.truncate()  
        print("完了")
if __name__=="__main__":
    firstsynchronize()      