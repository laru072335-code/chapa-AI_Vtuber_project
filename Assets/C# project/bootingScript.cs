using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;

public class bootingScript : MonoBehaviour
{

    [SerializeField] private Button Unity;//会話モード
    [SerializeField] private Button Stream;
    [SerializeField] private Button Test;

    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        Unity.onClick.AddListener(UnityClick);
        Stream.onClick.AddListener(StreamClick);
        Test.onClick.AddListener(TestClick);
    }

    private void UnityClick()
    {
        SceneManager.LoadScene("conversationScene");
    }
    private void StreamClick()
    {
        SceneManager.LoadScene("streamScene");

    }
    private void TestClick()
    {
        SceneManager.LoadScene("testScene");
    }
    // Update is called once per frame
}
