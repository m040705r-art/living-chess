using System.Collections;
using UnityEngine;

// One living statue on the board: plays its Blender clips, walks without foot sliding, crumbles.
public class ChessPiece : MonoBehaviour
{
    [System.Serializable]
    class WalkData { public string clip; public float cycleSeconds; public float[] speed; }

    public Animator animator;
    [Tooltip("BlenderSource/export.py writes <Piece>_walk.json: forward speed per phase of the Walk cycle that keeps the planted foot locked to the board.")]
    public TextAsset walkCurve;

    static readonly int CrumbleId = Shader.PropertyToID("_Crumble");
    Renderer[] rends;
    MaterialPropertyBlock mpb;
    float[] walkSpeed;

    public Transform[] Bones { get; private set; }
    public Renderer MainRenderer => rends[0];

    void Awake()
    {
        rends = GetComponentsInChildren<Renderer>();
        mpb = new MaterialPropertyBlock();
        Bones = GetComponentInChildren<SkinnedMeshRenderer>().bones;
        walkSpeed = walkCurve ? JsonUtility.FromJson<WalkData>(walkCurve.text).speed : new[] { 0.3f };
    }

    public bool IsPlaying(string clip) => animator.GetCurrentAnimatorStateInfo(0).IsName(clip) || animator.GetNextAnimatorStateInfo(0).IsName(clip);

    public Transform Bone(string name)
    {
        foreach (var b in Bones) if (b.name == name) return b;
        return null;
    }

    // Cross-fades to a clip (states in the controller are named after the clips); returns its length in seconds.
    public float Play(string clip, float fade = 0.2f)
    {
        animator.CrossFadeInFixedTime(clip, fade);
        foreach (var c in animator.runtimeAnimatorController.animationClips)
            if (c.name == clip) return c.length;
        return 0f;
    }

    public void SetCrumble(float v)
    {
        foreach (var r in rends)
        {
            r.GetPropertyBlock(mpb);
            mpb.SetFloat(CrumbleId, v);
            r.SetPropertyBlock(mpb);
        }
    }

    // Walk clip plays in place; the piece advances by the measured speed for the current phase of the cycle,
    // so the foot carrying the weight stays planted (a constant speed made the feet skate).
    // speed > 1 hurries a long walk across the board: the clip and the stride speed up together, so feet stay planted
    public IEnumerator WalkTo(Vector3 target, float speed = 1f)
    {
        Play("Walk");
        animator.speed = speed;
        while (true)
        {
            bool blending = animator.IsInTransition(0);
            var st = blending ? animator.GetNextAnimatorStateInfo(0) : animator.GetCurrentAnimatorStateInfo(0);
            float weight = blending ? animator.GetAnimatorTransitionInfo(0).normalizedTime : 1f;
            float phase = Mathf.Repeat(st.normalizedTime, 1f);
            float v = walkSpeed[Mathf.Min(walkSpeed.Length - 1, (int)(phase * walkSpeed.Length))] * weight;

            Vector3 to = target - transform.position; to.y = 0;
            float step = v * speed * Time.deltaTime;
            if (to.magnitude <= Mathf.Max(step, 1e-4f)) break;
            transform.position += to.normalized * step;
            yield return null;
        }
        transform.position = new Vector3(target.x, transform.position.y, target.z);
        animator.speed = 1f;
    }
}
