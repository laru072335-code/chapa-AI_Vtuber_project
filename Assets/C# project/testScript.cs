using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;
/*
動作のテスト用
接続のテストは含まれず、字幕の表示、Viseme,Auが正しく動くかをテストするためのもの
*/
public class testScript : MonoBehaviour
{
    [SerializeField]
    float[] au;//長さ9にする。
    [SerializeField]
    string prompt;
    [SerializeField]
    string answer;
    [SerializeField]
    string[] viseme;
    [SerializeField]
    float[] viseme_time;
    VisemeScript visemeScript;
    AuScript auScript;
    SubtitleScript subtitleScript;
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        visemeScript = GetComponent<VisemeScript>();
        auScript = GetComponent<AuScript>();
        subtitleScript = GetComponent<SubtitleScript>();

    }

    // Update is called once per frame
    void Update()
    {
        //キーの入力によってテストする
        var keyboard = Keyboard.current;
        //AUの送信テスト
        if (keyboard.aKey.wasPressedThisFrame)
        {
            Debug.Log("akey");
            auScript.SetAU(au);
        }
        //Visemeのテスト
        if (keyboard.vKey.wasPressedThisFrame)
        {
            Debug.Log("vkey");
            List<Viseme> visemes = new List<Viseme>() { new Viseme("o", (float)0.33152533173561094), new Viseme("o", (float)0.3985613793134689), new Viseme("e", (float)0.5282562024891376), new Viseme("u", (float)0.676918862760067), new Viseme("e", (float)0.9820178434252739) };
            foreach (Viseme viseme in visemes)
            {
                viseme.Change_Shape_key();
            }
            visemeScript.SetVisemes(visemes);
        }
        //字幕のテスト
        if (keyboard.sKey.wasPressedThisFrame)
        {
            Debug.Log("skey");
            Subtitles subtitles = new Subtitles(prompt, answer);
            subtitleScript.Display(subtitles);
        }

    }
}
