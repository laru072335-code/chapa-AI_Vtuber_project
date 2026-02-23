using UnityEngine;
using NativeWebSocket;
using MessagePack;
using System.Collections.Generic;

//pythonからvisemeデータを受け取り、反映するプログラム

[MessagePackObject]
public class Recive_wedsocket_type
{
    [Key(0)]
    public List<viseme> viseme { get; set; }
    [Key(1)]
    public string Subtitle { get; set; }
}
[MessagePackObject]
public class viseme
{
    [Key(0)]
    public string? Shape_key { get; set; }
    [Key(1)]
    public float Shape_key_time_value { get; set; }
    public override string ToString()
    {
        return $"{Shape_key},{Shape_key_time_value}";
    }
    public float ToSingle()
    {
        return Shape_key_time_value;
    }
    public void Change_Shape_key()
    {
        switch (Shape_key)
        {
            case "a":
                Shape_key = "あ";
                break;
            case "i":
                Shape_key = "い";
                break;
            case "u":
                Shape_key = "う";
                break;
            case "e":
                Shape_key = "え";
                break;
            case "o":
                Shape_key = "お";
                break;
            //ここより下のケースは、将来、mbpに置き換えるようにする。    
            case "n":
                Shape_key = null;
                break;
            case "pau":
                Shape_key = null;
                break;
            case "cl":
                Shape_key = null;
                break;
            default:
                Debug.Log("例外の音素があります。");
                break;

        }
    }
}


public class WebSocketScript : MonoBehaviour
{
    WebSocket ws;
    float[] recive_list = new float[27];
    float timer = 0f;
    List<viseme> data = new List<viseme>();
    [SerializeField] private SubtitleScript sb;
    private SkinnedMeshRenderer skinnedMeshRenderer;
    Dictionary<string, float> recive_lis = new Dictionary<string, float>() { { "au1L", 0 }, { "au1R", 0 }, { "au2R", 0 }, { "au2L", 0 }, { "au4L", 0 }, { "au4R", 0 }, { "au5L", 0 }, { "au5R", 0 }, { "au6L", 0 }, { "au6R", 0 }, { "au12L", 0 }, { "au12R", 0 }, { "au15L", 0 }, { "au15R", 0 }, { "au22", 0 }, { "au25", 0 }, { "au26", 0 }, { "au27", 0 }, { "au43L", 0 }, { "au43R", 0 }, { "a", 0 }, { "i", 0 }, { "u", 0 }, { "e", 0 }, { "o", 0 }, { "mbp", 0 }, { "fv", 0 } };
    readonly List<string> shapekeyname_list = new List<string>() { "au1L", "au1R", "au2L", "au2R", "au4L", "au4R", "au5L", "au5R", "au6L", "au6R", "au12L", "au12R", "au15L", "au15R", "au22", "au25", "au26", "au27", "au43L", "au43R", "a", "i", "u", "e", "o", "mbp", "fv" };
    readonly List<string> shapekeyname_list_beta = new List<string>() { "あ", "い", "う", "え", "お" };



    async void Start()
    {
        skinnedMeshRenderer = GetComponent<SkinnedMeshRenderer>();
        ws = new WebSocket("ws://localhost:8765");


        ws.OnOpen += () =>
        {

            Debug.Log("✅ Connected to Python server");
            ws.SendText("start!!");
        };
        ws.OnMessage += (bytes) =>//メッセージを受け取ったとき
        {
            var recive = MessagePackSerializer.Deserialize<Recive_wedsocket_type>(bytes);
            Debug.Log("今受信しました。");
            timer = 0f;
            data = recive.viseme;
            Debug.Log(recive.Subtitle);
            sb.Display(recive.Subtitle);//字幕表示
            //この部分は一時的なshape_keyの名前の不一致によるもの
            foreach (var item in data)
            {
                item.Change_Shape_key();
                //Debug.Log(item);

                //Debug.Log($"Key: {shapekey}, Value: {shapekey_time}");
            }
            //前の実装

            //ws.SendText("r");//readyの略

            /*if (bytes.Length % 4 == 0)
            {
                while (bytes.Length > count)
                {
                    for (int i = 0; i == bytes.Length - 1; i++)
                    {
                        recive = BitConverter.ToSingle(bytes, 0);
                        Debug.Log(recive);
                        recive_list[i] = recive;
                    }

                }
            }
            else
            {
                Debug.LogWarning("送られてきたバイト列の長さが正しくありません。");
            }
            Debug.Log($"📩 From Python(length):{bytes.Length}");*/
        };

        ws.OnError += (e) => Debug.Log("❌ Error: " + e);
        ws.OnClose += (e) => Debug.Log("🚪 Disconnected");
        await ws.Connect();

    }
    public void SetShapeByName(string? shapeName, float value)
    {
        if (shapeName != null)
        {
            if (value < 0)
            {
                value = 0;
            }
            // 名前からインデックス番号を探す
            int index = skinnedMeshRenderer.sharedMesh.GetBlendShapeIndex(shapeName);
            if (index != -1)
            {
                skinnedMeshRenderer.SetBlendShapeWeight(index, value);
                /*if (value != 0)
                {
                    Debug.Log($"{shapeName},{value}");
                }*/
            }
            else
            {
                Debug.LogWarning("シェイプキー " + shapeName + " が見つかりません。");
            }
        }
    }

    async void Update()
    {
        ws.DispatchMessageQueue();
        timer += Time.deltaTime;

        if (data == null || data.Count == 0)
        {
            foreach (viseme vowel in data)
            {
                Debug.Log(vowel);
            }
            foreach (string item in shapekeyname_list_beta)//ここが一回しか動かない
            {
                int index = skinnedMeshRenderer.sharedMesh.GetBlendShapeIndex(item);
                //重さ取得
                float weight = skinnedMeshRenderer.GetBlendShapeWeight(index);
                SetShapeByName(item, weight - 5);
            }
        }
        else
        {
            //Debug.Log(timer);
            if (timer <= data[data.Count - 1].Shape_key_time_value)
            {
                for (int index = 0; index < data.Count; index++)
                {

                    float targetTime = data[index].Shape_key_time_value;
                    float startTime = (index > 0) ? data[index - 1].Shape_key_time_value : 0f;

                    // 今、このデータの時間範囲内にいるか？
                    if (timer >= startTime && timer <= targetTime)
                    {
                        float duration = targetTime - startTime; // 区間の長さ
                        float relativeTime = timer - startTime; // 区間開始からの経過時間

                        // 0.0〜1.0 の割合（進捗度）を出す
                        float progress = relativeTime / duration;

                        // 1. 今の音を「0から100」へ増やす
                        SetShapeByName(data[index].Shape_key, progress * 100f);

                        // 2. 前の音があるなら、「100から0」へ減らす
                        if (index > 0)
                        {
                            SetShapeByName(data[index - 1].Shape_key, (1f - progress) * 100f);
                        }
                    }
                }
            }
            else
            {
                data.Clear();
                sb.Hide();//ここに字幕削除の処理
                Debug.Log("data reset");
            }

        }
    }
    private async void OnApplicationQuit()
    {
        await ws.Close();
    }
}
