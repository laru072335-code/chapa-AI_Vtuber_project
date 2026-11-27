using UnityEngine;
using NativeWebSocket;
using System.Threading.Tasks;
using TMPro;
using UnityEngine.UI;
using MessagePack;
using MessagePack.Formatters;

public class Inputer : MonoBehaviour
{
    [SerializeField]
    private WebSocketScript webSocketScript;

    [SerializeField] private TMP_InputField inputField;//input

    [SerializeField] private Button send;//送信用ボタン
    [SerializeField] private string user_name;//送信用ボタン

    [Header("テスト送信設定")]
    [SerializeField]
    private string testMessage = "Hello from Inputer";

    private void Start()
    {

    }

    private async void Update()
    {
        // 例: Spaceキーを押した時にWebSocketの状態を確認してメッセージを送信
        if (send.IsPressed())
        {
            if (string.IsNullOrWhiteSpace(inputField.text)) return;
            await SendInputMessage(inputField.text);
            inputField.text = "";
            inputField.ActivateInputField();
        }
    }

    /// <summary>
    /// WebSocketの状態を確認した上でメッセージを送信するメソッド
    /// </summary>
    public async Task SendInputMessage(string prompt)
    {
        if (webSocketScript == null)
        {
            Debug.LogError("[Inputer] NewWebSocketScript の参照が設定されていません。");
            return;
        }
        Message message = new Message(user_name, prompt, Authority.@private);
        byte[] bytes = MessagePackSerializer.Serialize(message);

        // 状態（ws_states）を確認
        WebSocketState currentState = webSocketScript.State;
        Debug.Log($"[Inputer] 現在のWebSocket状態: {currentState}");

        if (currentState == WebSocketState.Open)
        {
            Debug.Log($"[Inputer] メッセージを送信します: {message}");
            await webSocketScript.SendBytesAsync(bytes);
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
