using UnityEngine;
using TMPro;
/*
Displayメソッドを介して受け取った、subtitlesデータを元に画面に表示するやつ。
*/

public class SubtitleScript : MonoBehaviour
{
    [SerializeField]
    float displayTime;
    [SerializeField]
    private TextMeshProUGUI prompt;
    [SerializeField]
    private TextMeshProUGUI answer;
    //private float timer=0f;
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        prompt.text = null;
        answer.text = null;
    }
    public void Display(Subtitles subtitles)
    /*
    画面に表示するためのメソッド、また表示時間のためのタイマーの初期化をしている
    */
    {
        //timer = 0f;
        prompt.text = subtitles.prompt;
        answer.text = subtitles.answer;
    }
    // Update is called once per frame
    void Update()
    {
        /*一旦今はなくす
        timer += Time.deltaTime;
        
        if (timer >= displayTime)
        {
            timer = 0f;
            prompt.text = null;
            answer.text = null;
        }*/
    }
}
