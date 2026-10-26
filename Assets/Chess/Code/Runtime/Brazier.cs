using UnityEngine;

// A brazier's fire on the ruin stage: the light and the flame tongues flicker (no particles, cheap on iGPU)
public class Brazier : MonoBehaviour
{
    public Light fireLight;
    public Transform[] flames;
    float seed, baseIntensity;
    Vector3[] baseScale;

    void Start()
    {
        seed = Random.value * 100;
        baseIntensity = fireLight.intensity;
        baseScale = new Vector3[flames.Length];
        for (int i = 0; i < flames.Length; i++) baseScale[i] = flames[i].localScale;
    }

    void Update()
    {
        float t = Time.time + seed;
        fireLight.intensity = baseIntensity * (1 + 0.12f * Mathf.Sin(t * 9) + 0.07f * Mathf.Sin(t * 23 + 1.3f));
        for (int i = 0; i < flames.Length; i++)
        {
            float k = 1 + 0.18f * Mathf.Sin(t * (11 + i * 3) + i * 2) + 0.08f * Mathf.Sin(t * 29 + i);
            float w = 1 - (k - 1) * 0.5f;   // a taller tongue gets thinner
            flames[i].localScale = new Vector3(baseScale[i].x * w, baseScale[i].y * k, baseScale[i].z * w);
        }
    }
}
