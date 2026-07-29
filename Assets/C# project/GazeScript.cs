using UnityEngine;
/*
目の僅かな動きを再現するためのもの
これは目線の対象に貼り付ける
そしてAnimation Riggingなどでそれを追尾するようにする。
*/

public class GazeScript : MonoBehaviour
{

    [SerializeField] float random_range_max;
    [SerializeField] float random_range_min;
    [SerializeField] float range;
    [SerializeField] Transform move_object;
    float timer;
    float change_between;

    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        change_between = Random.Range(random_range_min, random_range_max);
    }

    // Update is called once per frame
    void Update()
    {
        timer += Time.deltaTime;
        if (timer > change_between)
        {
            timer = 0;
            change_between = Random.Range(random_range_min, random_range_max);
            move_block();
        }
    }
    void move_block()
    /*
    指定の範囲内で、ランダムに結び付けられたオブジェクトを動かす。
    */
    {
        Vector3 move_position = Random.insideUnitSphere * range;
        move_object.position = transform.position + move_position;
    }
}
