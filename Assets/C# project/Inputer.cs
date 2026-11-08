using UnityEngine;
using NativeWebSocket;
using System.Threading.Tasks;
using System.Text.Json.Serialization;

// 小文字（camelCase）でシリアライズされるようにコンバーターを指定
[JsonConverter(typeof(JsonStringEnumConverter))]
public enum MediaType
{
    text,
    image,
    video,
    sound,
    file
}
[JsonConverter(typeof(JsonStringEnumConverter))]
public enum Authority
{
    @private,
    @public
}
public class Message
{
    public string user_name; // ユーザーの名前
    public string content; // コンテンツ 将来は画像データとかも入る
    public MediaType type; //コンテンツのデータがテキストか画像かなどを指定
    public Authority authority; //権限設定
    readonly string detail = null; //細かい権限情報などを送る用、今はnull
}
public class Inputer : MonoBehaviour
{
    [SerializeField]
    private NewWebSocketScript webSocketScript;

    [Header("テスト送信設定")]
    [SerializeField]
    private string testMessage = "Hello from Inputer";

    private void Start()
    {

    }

    private async void Update()
    {
        // 例: Spaceキーを押した時にWebSocketの状態を確認してメッセージを送信
        if (Input.GetKeyDown(KeyCode.KeypadEnter))
        {
            await SendInputMessage(testMessage);
        }
    }

    /// <summary>
    /// WebSocketの状態を確認した上でメッセージを送信するメソッド
    /// </summary>
    public async Task SendInputMessage(string message)
    {
        if (webSocketScript == null)
        {
            Debug.LogError("[Inputer] NewWebSocketScript の参照が設定されていません。");
            return;
        }

        // 状態（ws_states）を確認
        WebSocketState currentState = webSocketScript.State;
        Debug.Log($"[Inputer] 現在のWebSocket状態: {currentState}");

        if (currentState == WebSocketState.Open)
        {
            Debug.Log($"[Inputer] メッセージを送信します: {message}");
            await webSocketScript.SendTextAsync(message);
        }
        else
        {
            Debug.LogWarning($"[Inputer] 送信できませんでした。接続が開いていません (状態: {currentState})");
        }
    }

    /// <summary>
    /// 外部から現在の接続状態を取得するためのメソッド
    /// </summary>
    public WebSocketState GetWebSocketState()
    {
        return webSocketScript != null ? webSocketScript.State : WebSocketState.Closed;
    }

    /// <summary>
    /// 接続中かどうかを判定するメソッド
    /// </summary>
    public bool IsConnected()
    {
        return webSocketScript != null && webSocketScript.IsConnected;
    }
}
