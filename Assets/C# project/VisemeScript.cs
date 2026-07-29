using System;
using System.Collections.Generic;
using UnityEngine;
/*
受け取ったデータから、visemeを指定のモデルに反映させるもの
*/

public class VisemeScript : MonoBehaviour
{
    private SkinnedMeshRenderer skinnedMeshRenderer;
    float timer;
    List<Viseme> visemes = new List<Viseme>();
    readonly List<string> shapekeyname_list_data = new List<string>() { "あ", "い", "う", "え", "お" };
    public void SetVisemes(List<Viseme> newVisemes)
    /*
    Visemeを受信スクリプトから受け取るもの
    */
    {
        visemes = newVisemes;
        timer = 0f; // データが新しくなったらタイマーをリセット
    }
    void Start()
    {
        skinnedMeshRenderer = GetComponent<SkinnedMeshRenderer>();
    }
    // Update is called once per frame
    void Update()
    {
        timer += Time.deltaTime;
        /*
        これはvisemeの動きを再現するためのもの
        */
        if (visemes == null || visemes.Count == 0)
        {
            //もし口が閉じなかった時の口を閉じる処理
            foreach (Viseme vowel in visemes)
            {
                Debug.Log(vowel);
            }
            foreach (string item in shapekeyname_list_data)
            {
                int index = skinnedMeshRenderer.sharedMesh.GetBlendShapeIndex(item);
                float weight = skinnedMeshRenderer.GetBlendShapeWeight(index);
                SetShapeByName(item, Mathf.MoveTowards(weight, 0f, 5f));
            }
        }
        else
        {
            Debug.Log(timer);
            if (timer <= visemes[visemes.Count - 1].Shapekey_time_value)
            {
                for (int index = 0; index < visemes.Count; index++)
                {

                    float targetTime = visemes[index].Shapekey_time_value;
                    float startTime = (index > 0) ? visemes[index - 1].Shapekey_time_value : 0f;

                    // 今、このデータの時間範囲内にいるか？
                    if (timer >= startTime && timer <= targetTime)
                    {
                        float duration = targetTime - startTime; // 区間の長さ
                        float relativeTime = timer - startTime; // 区間開始からの経過時間

                        // 0.0〜1.0 の割合（進捗度）を出す
                        float progress = relativeTime / duration;

                        // 1. 今の音を「0から100」へ増やす

                        SetShapeByName(visemes[index].Shape_key, Mathf.Lerp(0f, 100f, progress));

                        // 2. 前の音があるなら、「100から0」へ減らす
                        if (index > 0)
                        {
                            SetShapeByName(visemes[index - 1].Shape_key, Mathf.Lerp(100f, 0f, progress));
                        }
                    }
                }
            }
            else
            {
                visemes.Clear();
            }

        }
    }

    public void SetShapeByName(string? shapeName, float value)
    /*
    シェイプキーを名前から指定して、それの値を変更するもの
    */
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
                if (value != 0)
                {
                    Debug.Log($"{shapeName},{value}");
                }
            }
            else
            {
                Debug.LogWarning("シェイプキー " + shapeName + " が見つかりません。");
            }
        }
    }
}
