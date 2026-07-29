using System.Collections.Generic;
using UnityEngine;
/*
受信用スクリプトから受け取ったデータを指定のタイミングで流すためのもの
*/

public class SoundAnimationandPlay
{
    public SoundData soundData;
    public List<Viseme> Visemes;
    public SoundAnimationandPlay(SoundData soundData, List<Viseme> visemes)
    {
        this.soundData = soundData;
        Visemes = visemes;
    }
}
public class ManagerScript : MonoBehaviour
{
    /*
    受け取ったデータを保存しておくもの
    */
    [SerializeField]
    VisemeScript visemeScript;
    [SerializeField]
    AuScript auScript;
    [SerializeField]
    SubtitleScript subtitleScript;
    [SerializeField]
    SoundScript soundScript;
    private AU_List au = null;
    private List<Viseme> viseme = null;
    private Subtitles subtitles = null;
    private SoundData Sound = null;
    private Queue<SoundAnimationandPlay> Soundplays = new Queue<SoundAnimationandPlay>();


    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        /*
        今は使っていない
        */
    }
    public void ThrowViseme(List<Viseme> visemes)
    {
        /*
        visemeデータを受け取る
        */
        viseme = visemes;
        if (!(viseme == null || Sound == null))//どっちもnull出ない時
        {
            SoundAnimationandPlay soundAnimationand = new SoundAnimationandPlay(Sound, viseme);
            Soundplays.Enqueue(soundAnimationand);
            Sound = null;
            viseme = null;
        }
    }
    public void ThrowAu(AU_List aUs)
    {
        /*
        auデータを受け取る
        */
        au = aUs;
    }
    public void ThrowSub(Subtitles sub)
    {
        /*
        字幕データを受け取る
        */
        subtitles = sub;
    }
    public void ThrowSound(SoundData sounddata)
    {
        /*
        音声データを受け取る
        */
        Sound = sounddata;
        if (!(viseme == null || Sound == null))//どっちもnull出ない時
        {
            SoundAnimationandPlay soundAnimationand = new SoundAnimationandPlay(Sound, viseme);
            Soundplays.Enqueue(soundAnimationand);
            Sound = null;
            viseme = null;
        }
    }
    // Update is called once per frame
    void Update()
    {
        if (!soundScript.IsPlaying() && Soundplays.Count > 0)
        {
            Tell(Soundplays.Dequeue());
        }
    }
    private void Tell(SoundAnimationandPlay animationandPlay)
    {
        /*
        一斉にデータをもとに動かす。
        */
        soundScript.SoundSet(animationandPlay.soundData);
        visemeScript.SetVisemes(animationandPlay.Visemes);
        soundScript.PlaySound();
        if (subtitles != null)
        {
            subtitleScript.Display(subtitles);
        }
        if (au != null)
        {
            auScript.SetAU(au.ToFloatList());
        }
        subtitles = null;
        au = null;

    }
}
