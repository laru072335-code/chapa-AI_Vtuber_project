using UnityEngine;

public class BlinkScript : MonoBehaviour
/*
ランダムな感覚で瞬きをさせるためのもの
*/
{
    private SkinnedMeshRenderer skinnedMeshRenderer;
    [SerializeField] int range_max;
    [SerializeField] int range_min;

    [SerializeField] string blink_shape_key_name1;
    [SerializeField] string blink_shape_key_name2;
    [SerializeField] float blink_time;
    int wait_time;
    int shape_key_index1;
    int shape_key_index2;

    float timer = 0;

    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        skinnedMeshRenderer = GetComponent<SkinnedMeshRenderer>();
        shape_key_index1 = skinnedMeshRenderer.sharedMesh.GetBlendShapeIndex(blink_shape_key_name1);//shapekeyのindex
        shape_key_index2 = skinnedMeshRenderer.sharedMesh.GetBlendShapeIndex(blink_shape_key_name2);//shapekeyのindex
        wait_time = init_for_blink();

    }

    // Update is called once per frame
    void Update()
    {
        timer += Time.deltaTime;
        if (timer > wait_time && wait_time + blink_time > timer)
        {
            // 瞬きするやつ
            // 割合をまず、(timer-wait_time)/(blink_time)でだしている。
            // そこから、*100をして%に変換
            float pacentage = ((timer - wait_time) / blink_time) * 100;
            if (pacentage < 50)
            {    //閉じる部分
                Blink(shape_key_index1, pacentage * 2);
                Blink(shape_key_index2, pacentage * 2);
            }
            else
            {
                //開ける部分
                //200-は逆数を取ろうとしている
                Blink(shape_key_index1, 200 - (pacentage * 2));
                Blink(shape_key_index2, 200 - (pacentage * 2));
            }
        }
        if (timer > wait_time + blink_time)
        {
            timer = 0;
            init_for_blink();
            Blink(shape_key_index1, 0);
            Blink(shape_key_index2, 0);
        }
    }
    void Blink(int shape_key_index, float value)
    /*
    シェイプキーの数値を変更して、瞬きさせるもの。値の決定はここでは行わない。
    */
    {
        skinnedMeshRenderer.SetBlendShapeWeight(shape_key_index, value);
    }
    int init_for_blink()
    /*
    瞬きの間の待ち時間の初期化
    */
    {
        int wait_blink_second = Random.Range(range_min, range_max);
        return wait_blink_second;
    }
}
