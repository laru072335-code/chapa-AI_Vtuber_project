using UnityEngine;
using NativeWebSocket;
using System.Threading.Tasks;
using MessagePack;
using System.Collections.Generic;
using TMPro;
using System;
public class WebSocketScript : MonoBehaviour
/*
受信して、それぞれの担当のスクリプトにそのデータを渡す
*/
{
    WebSocket ws;
    // 外部からWebSocketの状態を確認するためのプロパティ
    public WebSocketState State => ws != null ? ws.State : WebSocketState.Closed;
    public bool IsConnected => ws != null && ws.State == WebSocketState.Open;

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
        ws.SendText("Connect");
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
                    Debug.Log("想定されていないデータが送られています。");
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

    /// <summary>
    /// 外部スクリプトからバイナリデータを送信するためのメソッド
    /// </summary>
    public async Task SendBytesAsync(byte[] bytes)
    {
        if (IsConnected)
        {
            await ws.Send(bytes);
        }
        else
        {
            Debug.LogWarning($"[NewWebSocketScript] 接続されていないため送信できませんでした (現在の状態: {State})");
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
