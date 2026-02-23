using UnityEngine;
using TMPro;
public class SubtitleScript : MonoBehaviour
{
    [SerializeField] private TextMeshProUGUI subtitleText;
    public void Display(string subtitle)
    {
        subtitleText.text = subtitle;
        subtitleText.gameObject.SetActive(true);
    }
    public void Hide()
    {
        subtitleText.text = "";
        subtitleText.gameObject.SetActive(false);
    }
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        Hide();
    }

    // Update is called once per frame
    void Update()
    {

    }
}
