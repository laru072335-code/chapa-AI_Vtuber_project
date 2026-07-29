using UnityEngine;
using NativeWebSocket;
using MessagePack;
using System.Collections.Generic;
using System;
using UnityEngine.SceneManagement;
using TMPro;
using System.Linq;
using UnityEngine.Scripting;
using System.Threading.Tasks;
/*
pythonからviseme、subtitles、AUを受け取って、それぞれのスクリプトに流し込むプログラム
*/
[MessagePackObject]
public class AU_List
/*
AUを受け取るためのクラス、このクラスの形に変換して扱う。
ただし、Listではあるが、foreachは使えない。インデックスの概念はある。
*/
{
    [Key(0)]
    public float au01;
    [Key(1)]
    public float au02;
    [Key(2)]
    public float au04;
    [Key(3)]
    public float au05;
    [Key(4)]
    public float au06;
    [Key(5)]
    public float au12;
    [Key(6)]
    public float au15;
    [Key(7)]
    public float au25;
    [Key(8)]
    public float au43;
    [Preserve]
    public AU_List(float[] aus)
    {
        au01 = aus[0];
        au02 = aus[1];
        au04 = aus[2];
        au05 = aus[3];
        au06 = aus[4];
        au12 = aus[5];
        au15 = aus[6];
        au25 = aus[7];
        au43 = aus[8];
    }
    public float[] ToFloatList()
    {
        /*
        floatの配列に変換するためのメソッド
        */
        float[] floats = new float[9];
        floats[0] = au01;
        floats[1] = au02;
        floats[2] = au04;
        floats[3] = au05;
        floats[4] = au06;
        floats[5] = au12;
        floats[6] = au15;
        floats[7] = au25;
        floats[8] = au43;
        return floats;
    }
    [Preserve]
    public AU_List() { }//WedSocket用の初期化
    public float this[int index]
    {
        /*
        インデックスの概念の追加
        */
        get
        {
            return index switch
            {
                0 => au01,
                1 => au02,
                2 => au04,
                3 => au05,
                4 => au06,
                5 => au12,
                6 => au15,
                7 => au25,
                8 => au43,
                _ => throw new IndexOutOfRangeException($"Index {index} は AU_List の範囲外です。")
            };
        }
        set
        {
            switch (index)
            {
                case 0: au01 = value; break;
                case 1: au02 = value; break;
                case 2: au04 = value; break;
                case 3: au05 = value; break;
                case 4: au06 = value; break;
                case 5: au12 = value; break;
                case 6: au15 = value; break;
                case 7: au25 = value; break;
                case 8: au43 = value; break;
                default: throw new IndexOutOfRangeException($"Index {index} は AU_List の範囲外です。");
            }
        }
    }
}

[MessagePackObject]
public class Subtitles
/*
字幕を受信する用のクラス
*/
{
    [Key(0)]
    public string prompt;
    [Key(1)]
    public string answer;
    [Preserve]
    public Subtitles(string prompt, string answer)
    {
        this.prompt = prompt;
        this.answer = answer;
    }
    public string Print()
    /*
    デバッグでプリントする用
    */
    {
        return $"prompt{prompt},answer{answer}\n";
    }

}
[MessagePackObject]
public class Viseme
/*
Visemeを受け取るためにクラス
*/
{
    [Key(0)]
    public string? Shape_key { get; set; }
    [Key(1)]
    public float Shapekey_time_value { get; set; }
    [Preserve]
    public Viseme(string Shape_key, float Shapekey_time_value)
    {
        this.Shape_key = Shape_key;
        this.Shapekey_time_value = Shapekey_time_value;
    }
    public string Print()
    /*
    デバッグでプリントする用
    */
    {
        return $"Shape_key{Shape_key},Shapekey_time_value{Shapekey_time_value}\n";
    }
    public void Change_Shape_key()
    /*
    シェイプキーの名前と送られてきた音素の名前が合わないときに、変換するもの
    */
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
[MessagePackObject]
public class SoundData
{
    [Key(0)]
    public int sampleRate;
    [Key(1)]
    public byte[] sound;
    public SoundData() { }

}

public class NewWebSocketScript : MonoBehaviour
/*
受信して、それぞれの担当のスクリプトにそのデータを渡す
*/
{
    WebSocket ws;
    [SerializeField]
    ManagerScript manager;
    [SerializeField]
    SoundScript sound;
    [SerializeField]//テスト用
    TextMeshProUGUI textMesh;
    bool isTestMode;
    bool RetryConnect;
    bool DisConnect = false;
    private async void Start()
    {
        string[] args = Environment.GetCommandLineArgs();
        isTestMode = args.Contains("--test-mode");
        //isTestMode = true;//editモードで実行するときだけ、有効にする。
        if (isTestMode)
        {
            if (SceneManager.GetActiveScene().name != "testScene")
            {
                SceneManager.LoadScene("testScene");
                //これはWebSocektのみのtest
                //test時の挙動についてはtestSceneを参照
            }
            else
            {
                General_Start();
            }
        }
        else
        {
            General_Start();
        }
    }
    private async void General_Start()
    /*
    一番最初に接続を試みるためのもの
    */
    {
        _ = Connect();
    }
    private async Task Connect()
    /*
    ここで接続を確立させようとしている。
    また、一番最初にWebSocket型の変数の中身をリセットしている。
    */
    {

        if (ws != null)
        {
            ws.OnOpen -= OnOpen;
            ws.OnMessage -= OnMessage;
            ws.OnError -= Onerror;
            ws.OnClose -= OnClose;
            if (ws.State == WebSocketState.Open || ws.State == WebSocketState.Connecting)
            {
                await ws.Close();
            }
        }
        ws = null;
        ws = new WebSocket("ws://127.0.0.1:8765");
        ws.OnOpen += OnOpen;
        ws.OnMessage += OnMessage;
        ws.OnError += Onerror;
        ws.OnClose += OnClose;
        try
        {
            await ws.Connect();
        }
        catch (Exception e)
        {
            Debug.LogWarning($"WebSocket接続自体に失敗しました: {e.Message}");
            if (!DisConnect)
            {
                await Retry();
            }
        }
    }
    private async Task Retry()
    /*
    接続がダメだったときに、1秒待って再接続を試みる
    */
    {
        if (RetryConnect) return;
        RetryConnect = true;
        await Task.Delay(1000);
        if (ws == null || ws.State == WebSocketState.Closed)
        {
            RetryConnect = false; // フラグを下ろしてから再接続
            await Connect();
        }
        else
        {
            RetryConnect = false;
        }

    }
    private void OnOpen()
    /*
    WebSocketが繋がったときに何をするか
    */
    {
        Debug.Log("✅ Connected to Python server");
        //textMesh.text = "✅ Connected to Python server";
        ws.SendText("Start");
    }
    private void OnMessage(byte[] bytes)
    /*
    通信を受け取ったときに何をするのか
    */
    {
        //詳しいエラー内容が知りたい時はtry-catchを外すといいかもしれない
        try
        {
            var reader = new MessagePackReader(bytes);
            int arrayLength = reader.ReadArrayHeader();
            int head = reader.ReadInt32();

            switch (head)
            {
                case 0://visemeの受信
                    List<Viseme> v = MessagePackSerializer.Deserialize<List<Viseme>>(ref reader);
                    //viseme
                    foreach (Viseme viseme in v)
                    {
                        viseme.Change_Shape_key();
                    }
                    if (isTestMode)
                    {
                        foreach (Viseme viseme in v)
                        {
                            textMesh.text += viseme.Print();
                        }
                    }
                    else
                    {
                        manager.ThrowViseme(v);
                    }
                    break;
                case 1://字幕の受信
                    Subtitles sub = MessagePackSerializer.Deserialize<Subtitles>(ref reader);
                    if (isTestMode)
                    {
                        textMesh.text += sub.Print();
                    }
                    else
                    {
                        manager.ThrowSub(sub);
                    }
                    break;
                case 2://auの受信
                    AU_List au = MessagePackSerializer.Deserialize<AU_List>(ref reader);
                    if (isTestMode)
                    {
                        for (int i = 0; i < 9; i++)
                        {
                            textMesh.text += $"au{au[i]}\n";
                        }
                    }
                    else
                    {
                        manager.ThrowAu(au);
                    }
                    break;
                case 3://音声(testは人の目で確認できるものではないため実際にながして判定する。)
                    var audioBytes = MessagePackSerializer.Deserialize<SoundData>(ref reader);
                    if (isTestMode)
                    {
                        sound.SoundSet(audioBytes);
                        sound.PlaySound();
                    }
                    else
                    {
                        manager.ThrowSound(audioBytes);
                    }
                    break;
                default:
                    if (isTestMode)
                    {
                        textMesh.text += "想定されていないデータが送られています。\n";
                    }
                    else
                    {
                        Debug.Log("想定されていないデータが送られています。");
                    }
                    break;
            }
        }
        catch (Exception e)
        {
            textMesh.text = $"{e}";
            ws.SendText(e.ToString());
            return;
        }
    }
    private void Onerror(string e)
    /*
    接続でエラーが出たときに何をするのか
    */
    {
        Debug.Log("❌ Error: " + e);
    }
    private async void OnClose(WebSocketCloseCode closeCode)
    /*
    接続ができなかったとき、切断されたときに何をするのか
    */
    {
        Debug.Log("🚪 Disconnected");
        if (!DisConnect)
        {
            await Retry();
        }
    }
    private async void Update()
    {
        if (ws != null && ws.State == WebSocketState.Open)
        {
            ws.DispatchMessageQueue();
        }
    }
    public async Task DisconnectAsync()
    /*
    意図的に接続を切るためのもの
    */
    {
        DisConnect = true;
        if (ws != null && (ws.State == WebSocketState.Open || ws.State == WebSocketState.Connecting))
        {
            await ws.Close();
        }
    }
    private async void OnApplicationQuit()
    {
        // アプリ終了時に意図しない再接続が走るのを防ぐ
        await DisconnectAsync();
    }
    private async void OnDestroy()
    {
        await DisconnectAsync();
    }
}
