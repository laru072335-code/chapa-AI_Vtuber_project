using UnityEngine;
using MessagePack;
using System;
using UnityEngine.Scripting;
using System.Text.Json.Serialization;
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
    readonly string detail = "a";  //細かい権限情報などを送る用、今はnull
}
