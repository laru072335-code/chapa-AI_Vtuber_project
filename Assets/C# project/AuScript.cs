using UnityEngine;
/*
受け取ったデータから、auを指定のモデルに反映させるもの
*/
public class AuScript : MonoBehaviour
{
    float timer;
    float percent;
    float[] start_au = new float[9];
    float[] target_aus = new float[9];
    readonly string[] au_name_list = new string[9] { "au01", "au02", "au04", "au05", "au06", "au12", "au15", "au25", "au43" };
    [SerializeField]
    float au_Rate_of_change;
    private SkinnedMeshRenderer skinnedMeshRenderer;
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        skinnedMeshRenderer = GetComponent<SkinnedMeshRenderer>();
    }
    public void SetAU(float[] aUs)
    {
        for (int i = 0; i < 9; i++)
        {
            int index = skinnedMeshRenderer.sharedMesh.GetBlendShapeIndex(au_name_list[i]);
            float weight = skinnedMeshRenderer.GetBlendShapeWeight(index);
            start_au[i] = weight;
        }
        target_aus = aUs;
        timer = 0f;

    }

    // Update is called once per frame
    void Update()
    {
        timer += Time.deltaTime;

        if (timer <= au_Rate_of_change)
        {
            percent = timer / au_Rate_of_change;
            for (int i = 0; i < 9; i++)
            {
                SetShapeByName(au_name_list[i], Mathf.Lerp(start_au[i], target_aus[i], percent));
            }
        }
        else
            if (timer < 2 * au_Rate_of_change)
            {
                percent = timer / (2 * au_Rate_of_change);
                for (int i = 0; i < 9; i++)
                {
                    SetShapeByName(au_name_list[i], Mathf.Lerp(target_aus[i], 0, percent));
                }
            }
    }
    void SetShapeByName(string? shapeName, float value)
    /*
    シェイプキーを名前から指定して、それの値を変更するもの
    */
    {
        //デフォルトは変化値を渡す。
        if (shapeName != null)
        {
            if (value < 0)
            {
                value = 0;
            }
            // 名前からインデックス番号を探す
            int index = skinnedMeshRenderer.sharedMesh.GetBlendShapeIndex(shapeName);
            //float weight = skinnedMeshRenderer.GetBlendShapeWeight(index);
            if (index != -1)
            {
                skinnedMeshRenderer.SetBlendShapeWeight(index, value);
                if (value != 0)
                {
                    //Debug.Log($"{shapeName},{value}");
                }
            }
            else
            {
                Debug.LogWarning("シェイプキー " + shapeName + " が見つかりません。");
            }
        }
    }
}
