using System;
using UnityEngine;

/*
音声を再生するためのもの
*/
public class SoundScript : MonoBehaviour
{
    [SerializeField] private AudioSource audioSource;

    private AudioClip loadedClip;

    public void SoundSet(SoundData data)
    {
        /*
        音声データの用意
        */
        int sampleRate = data.sampleRate;
        byte[] rawBytes = data.sound;
        if (rawBytes == null || rawBytes.Length == 0)
        {
            Debug.LogError("音声データが空です。");
            return;
        }
        try
        {
            float[] floatSamples = new float[rawBytes.Length / 4];
            Buffer.BlockCopy(rawBytes, 0, floatSamples, 0, rawBytes.Length);
            int channels = 1; //モノラル
            loadedClip = AudioClip.Create("VOICEVOX_Voice", floatSamples.Length, channels, sampleRate, false);
            loadedClip.SetData(floatSamples, 0);
            Debug.Log($"音声の準備が完了しました！(サンプル数: {floatSamples.Length}, レート: {sampleRate}Hz)");
        }
        catch (Exception e)
        {
            Debug.LogError($"音声データの変換に失敗しました: {e.Message}");
        }
    }

    public void PlaySound()
    {
        // まだ読み込みが終わっていないかチェック
        if (loadedClip == null)
        {
            Debug.LogWarning("まだ音声の準備ができていません！");
            return;
        }

        // 準備しておいたデータをAudioSourceにセットして流す！
        audioSource.clip = loadedClip;
        audioSource.Play();
    }
    public bool IsPlaying()
    {
        if (audioSource != null)
        {
            return audioSource.isPlaying;
        }
        return false;
    }
}
