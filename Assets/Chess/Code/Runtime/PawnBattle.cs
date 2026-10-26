using System.Collections;
using System.Collections.Generic;
using UnityEngine;

// Battle demos from the user's storyboard. Loops.
//  PawnVsPawn (row 1, same as WebPreview/index.html): advance -> daggers clash -> thrust taken on the crossed daggers ->
//    counter drives white back -> killing thrust, black crumbles while it falls, rubble fades away, white wins.
//  KnightVsPawn (row 2, revised): the knight glides along its L-move, spears the pawn on the way down, lands short,
//    walks into the square and rears in triumph.
//  KingVsPawn (row 6): an overhead greatsword cleave from one square; the blade bites the board and a golden shockwave rings out.
// Rule: a weapon reaching the BODY kills; every earlier blow lands on a weapon (the pawn's crossed daggers).
public class PawnBattle : MonoBehaviour
{
    public enum Matchup { PawnVsPawn, KnightVsPawn, BishopVsPawn, RookVsPawn, QueenVsPawn, KingVsPawn }
    public Matchup matchup;
    public ChessPiece white, black;
    public Material stoneMaterial;            // template for rubble (Chess/Stone)
    public Transform cameraPivot;
    public float orbitSpeed = 4f;             // degrees per second
    [Tooltip("Off in the playable game (ChessGame drives the pieces and borrows the effects below)")]
    public bool autoPlay = true;
    [Tooltip("Assets/Chess/Audio (SoundSource/sfx.py). Variants named name_1, name_2... are picked at random.")]
    public AudioClip[] sfxClips;
    [Tooltip("Sound is off for now (user: 音はまだつけなくていい); ChessSceneBuilder.SoundOn turns it back on")]
    public bool soundOn;

    const float HitTime = 0.625f;             // spear point lands on frame 16 of every attack / defence clip
    const float ClashTime = 0.583f;           // spears cross on frame 15 of Clash

    readonly Vector3 whiteStart = new Vector3(0, 0, 2), whiteFight = new Vector3(0, 0, 0), blackSpot = new Vector3(0, 0, -1);
    ParticleSystem sparks;
    readonly List<Rubble> rubble = new List<Rubble>();

    class Rubble { public Transform t; public Vector3 v; public float r, spin; public Renderer rend; }

    void Start()
    {
        Application.targetFrameRate = 60;   // steady 60 fps (iGPU target); vSync caps it on 60 Hz screens anyway
        sparks = MakeSparks();
        InitAudio();
        if (!autoPlay) return;
        foreach (var p in new[] { white, black }) if (p.Bone("weapon.L")) AddTrails(p, 0.3f);
        if (matchup == Matchup.QueenVsPawn) AddTrails(white, 0.9f);
        if (matchup == Matchup.KingVsPawn) AddTrails(white, 0.85f);
        if (matchup == Matchup.KnightVsPawn) AddTrails(white, 1.1f);
        StartCoroutine(Loop());
    }

    [System.NonSerialized] public float shake;
    Vector3 camRest;

    void LateUpdate()
    {
        var cam = Camera.main ? Camera.main.transform : null;
        if (cam == null) return;
        if (camRest == Vector3.zero) camRest = cam.localPosition;
        cam.localPosition = camRest + (shake > 0.001f ? Random.insideUnitSphere * shake : Vector3.zero);   // impact kick
        shake *= Mathf.Pow(0.02f, Time.deltaTime);
    }

    readonly List<(ChessPiece p, TrailRenderer tr)> trails = new List<(ChessPiece, TrailRenderer)>();

    void Update()
    {
        foreach (var (p, tr) in trails)   // afterimages only for the spinning slash (user: "双剣の残影は回転切りの時だけ")
            if (p && tr) tr.emitting = p.gameObject.activeSelf && (p.IsPlaying("Attack")   // pawns (twin daggers): the spin only
                          || !p.Bone("weapon.L") && (p.IsPlaying("AttackBlocked") || p.IsPlaying("LeapAttack")));
        if (cameraPivot) cameraPivot.Rotate(0, orbitSpeed * Time.deltaTime, 0, Space.World);
        StepRubble(Time.deltaTime);
    }

    IEnumerator Loop()
    {
        while (true)
        {
            Place();
            white.Play("Idle", 0); black.Play("Idle", 0);
            if (matchup != Matchup.PawnVsPawn) StartCoroutine(DrawLater(black, matchup == Matchup.KnightVsPawn ? 0.4f : 1f));   // the pawn sees it coming
            // the knight alternates its two showings: the big sweep (user: "豪快な一払い") and the glide along its L
            if (matchup == Matchup.KnightVsPawn) { yield return (knightRound++ % 2 == 0) ? KnightSweep() : KnightLeap(); continue; }
            yield return new WaitForSeconds(1.5f);
            // the knight's lance strikes from 1.5 squares (BlenderSource/knight_anims.py KN_REACH)
            // the knight's lance strikes from 1.5 squares, the bishop's bolt from 2.2
            // the rook's tackle covers ~1 square itself, so it stops 1.6 out; the queen's blade sweeps from 1.3
            // the king swings its first, blocked cleave from 1.65 squares (king_anims KING_DUEL_BLOCK), then steps in
            float reach = matchup == Matchup.KnightVsPawn ? 0.5f : matchup == Matchup.BishopVsPawn ? 1.2f
                        : matchup == Matchup.RookVsPawn ? 0.6f : matchup == Matchup.QueenVsPawn ? 0.3f
                        : matchup == Matchup.KingVsPawn ? 0.65f : 0f;
            if (matchup == Matchup.RookVsPawn) yield return RookCharge(whiteFight + new Vector3(0, 0, reach));
            else yield return white.WalkTo(whiteFight + new Vector3(0, 0, reach));
            if (matchup != Matchup.RookVsPawn) { white.Play("Idle"); yield return new WaitForSeconds(0.4f); }   // the rook runs straight in
            // battle sheet: every blow before the last is met by a blade or a guard
            if (matchup == Matchup.QueenVsPawn) { yield return QueenSpell(); continue; }   // she never strikes: magic only
            else if (matchup == Matchup.KingVsPawn)
            {
                yield return PieceBlocked(0.945f);
                yield return PawnCounter(0.65f);
                yield return white.WalkTo(whiteFight);
                white.Play("Idle", 0.15f); yield return new WaitForSeconds(0.2f);
            }
            if (matchup != Matchup.PawnVsPawn && matchup != Matchup.BishopVsPawn) { yield return KnightCharge(); continue; }   // same beat: contact on frame 16
            if (matchup == Matchup.BishopVsPawn) { yield return BishopCast(true); yield return BishopSpell(); continue; }

            // both draw their daggers from the belt and drop into guard
            float dr = white.Play("Draw", 0.1f); black.Play("Draw", 0.1f);
            StartCoroutine(SfxLater("draw", white.transform.position + Vector3.up * 0.6f, 0.3f, 0.7f));
            StartCoroutine(SfxLater("draw", black.transform.position + Vector3.up * 0.6f, 0.36f, 0.6f));
            yield return new WaitForSeconds(dr);
            white.Play("Ready"); black.Play("Ready"); yield return new WaitForSeconds(0.4f);

            // design sheets "ポーン（双剣）": a clash, then combo / heavy attack / parry-and-counter / rush, every blow landing
            // on the other's crossed blades, then the pursuit's spinning slash kills
            var mid = (white.transform.position + black.transform.position) * 0.5f + Vector3.up * 0.74f;
            yield return Exchange(white, "Clash", black, "Clash", mid, ClashTime);
            // second storyboard: strings flow straight into each other (no stop in guard between them)
            yield return String(white, "Combo", black, "DefendCombo");
            yield return String(black, "Heavy", white, "DefendHeavy");
            yield return String(white, "Counter", black, "Parried");
            yield return String(black, "Rush", white, "DefendRush");

            // the pursuit: the spin slash cuts through the body
            float d = white.Play("Attack");
            float dd = black.Play("Death");
            var dying = StartCoroutine(DieCrumbling(black, dd * 0.75f, 0.29f));
            StartCoroutine(SfxLater("swing", white.transform.position + Vector3.up * 0.7f, HitTime - 0.12f, 0.7f));
            StartCoroutine(SfxLater("hit", black.transform.position + Vector3.up * 0.7f, HitTime, 0.9f));
            yield return new WaitForSeconds(d + 0.3f);
            white.Play("Victory");
            yield return dying;
            yield return new WaitForSeconds(2.5f);
        }
    }

    // the knight's move (BlenderSource/knight_anims.py): the clip carries height and pitch; the knight is carried
    // across the board linearly between KnTakeoff and KnTouch. LeapAttack lands KnLandShort short of the target.
    int knightRound;
    // knight_anims.py Sweep: the pawn stands at the knight's right front (KN_SWEEP_PAWN) and is swept away on frame 24
    const int KnSweep = 24;
    IEnumerator KnightSweep()
    {
        white.transform.position = new Vector3(0, 0, 0); white.transform.rotation = Quaternion.Euler(0, 180, 0);
        var spot = white.transform.TransformPoint(new Vector3(0.55f, 0, 0.62f));   // clip (-0.55, -0.62), knight facing -Z
        black.transform.position = spot;
        black.transform.rotation = Quaternion.LookRotation(white.transform.position - spot);
        yield return new WaitForSeconds(1.0f);
        float dr = white.Play("Draw", 0.15f); StartCoroutine(SfxLater("draw", white.transform.position + Vector3.up * 0.9f, 0.3f, 0.8f));
        yield return new WaitForSeconds(dr);
        white.Play("Idle", 0.15f); yield return new WaitForSeconds(0.4f);
        float d = white.Play("Sweep", 0.15f);
        StartCoroutine(SfxLater("swing", white.transform.position + Vector3.up * 1f, (KnSweep - 5) / 24f, 1f));
        float dd = black.Play("DieToKnightSweep", 0.1f);
        var dying = StartCoroutine(DieCrumbling(black, dd * 0.75f, (KnSweep / 24f) / (dd * 0.75f)));
        yield return new WaitForSeconds(6 / 24f); Dust(white.transform.position, 1.1f);
        yield return new WaitForSeconds((KnSweep - 6) / 24f);
        var at = spot + Vector3.up * 0.7f;
        Spark(at); Spark(at); StartCoroutine(ShockWave(spot)); Dust(spot, 2f); shake = 0.16f;
        Sfx("hit", at, 1f); Sfx("clash", at, 0.6f);
        Color tint = black.MainRenderer.sharedMaterial.GetColor("_Color");
        for (int i = 0; i < 16; i++) Chunk(at, 0.02f, 2.6f, tint);
        yield return new WaitForSeconds(d - KnSweep / 24f);
        white.Play("Victory");
        yield return dying;
        yield return new WaitForSeconds(2.5f);
    }

    const int KnTakeoff = 10, KnTouch = 34, KnHit = 30;
    const float KnLandShort = 0.6f;
    IEnumerator KnightLeap()
    {
        var start = blackSpot + new Vector3(1, 0, 2);   // an L: one across, two forward
        white.transform.position = start;
        var dir = (blackSpot - start).normalized;
        white.transform.rotation = Quaternion.LookRotation(dir);
        yield return new WaitForSeconds(2.3f);
        var land = start + dir * ((blackSpot - start).magnitude - KnLandShort);
        float d = white.Play("LeapAttack", 0.1f);
        Coroutine dying = null;
        bool hit = false;
        for (float t = 0; t < d; t += Time.deltaTime)
        {
            float f = t * 24f;
            white.transform.position = Vector3.Lerp(start, land, Mathf.Clamp01((f - KnTakeoff) / (KnTouch - KnTakeoff)));
            if (dying == null && f >= KnHit - 16)   // the pawn's Death takes the blow on its frame 16
            {
                float dd = black.Play("Death");
                dying = StartCoroutine(DieCrumbling(black, dd * 0.75f, 0.29f));
            }
            if (!hit && f >= KnHit)
            {
                hit = true;
                var at = black.transform.position + Vector3.up * 0.68f;
                Spark(at); shake = 0.08f; Sfx("hit", at, 1f);
                Color tint = black.MainRenderer.sharedMaterial.GetColor("_Color");
                for (int i = 0; i < 14; i++) Chunk(at, 0.018f, 2.2f, tint);
            }
            yield return null;
        }
        white.transform.position = land;
        yield return white.WalkTo(blackSpot);   // into the captured square
        white.Play("Victory");
        yield return dying;
        yield return new WaitForSeconds(2.5f);
    }

    // hit frames of the pawn's strings (BlenderSource/anims.py PAWN_COMBOS; 0 bone = the parried thrust on the X)
    static readonly Dictionary<string, (int f, string bone)[]> Hits = new Dictionary<string, (int, string)[]>
    {
        { "Combo", new[] { (9, "weapon"), (14, "weapon.L"), (19, "weapon"), (24, "weapon.L"), (32, "weapon"), (37, "weapon.L") } },
        { "Heavy", new[] { (17, "weapon"), (23, "weapon.L"), (29, "weapon") } },
        { "Rush", new[] { (8, "weapon"), (11, "weapon.L"), (14, "weapon"), (17, "weapon.L"), (20, "weapon"), (26, "weapon.L"), (29, "weapon"), (32, "weapon.L") } },
        { "Counter", new[] { (16, "x"), (26, "weapon"), (31, "weapon.L"), (36, "weapon") } },
    };
    const float Cut = 0.306f;   // the point 85% along the blade that the cuts are solved onto

    IEnumerator String(ChessPiece a, string clipA, ChessPiece b, string clipB)
    {
        float d = Mathf.Max(a.Play(clipA, 0.15f), b.Play(clipB, 0.15f)), t = 0;
        foreach (var (f, bone) in Hits[clipA])
        {
            float swish = Mathf.Max(t, f / 24f - 0.1f);
            yield return new WaitForSeconds(swish - t); t = swish;
            Sfx("swing", a.transform.position + Vector3.up * 0.7f, 0.45f, 0.12f);
            yield return new WaitForSeconds(f / 24f - t); t = f / 24f;
            var at = bone == "x" ? ShieldFace(a, b) : a.Bone(bone).TransformPoint(0, Cut, 0);
            Spark(at); shake = 0.025f;
            Sfx("clash", at, 0.75f, 0.08f);
        }
        yield return new WaitForSeconds(d - t - 0.12f);   // the next string fades in just before this one ends
    }

    IEnumerator Exchange(ChessPiece a, string clipA, ChessPiece b, string clipB, Vector3? sparkAt, float at)
    {
        float d = Mathf.Max(a.Play(clipA, 0.12f), b.Play(clipB, 0.12f));
        yield return new WaitForSeconds(at);
        if (sparkAt.HasValue) { Spark(sparkAt.Value); shake = 0.03f; Sfx("clash", sparkAt.Value, 0.9f); }
        yield return new WaitForSeconds(d - at);
    }

    // blade trails (design sheet: arcs of light behind fast cuts), one per dagger, from guard to point
    public void ClearTrails() => trails.Clear();   // the game respawns its pieces

    public void AddTrails(ChessPiece p, float along)
    {
        var mat = new Material(Shader.Find("Legacy Shaders/Particles/Additive"));
        foreach (var name in new[] { "weapon", "weapon.L" })
        {
            var bone = p.Bone(name); if (!bone) continue;
            var go = new GameObject("Trail");
            go.transform.SetParent(bone, false);
            go.transform.localPosition = new Vector3(0, along, 0);   // near the point (bone Y runs along the blade)
            var tr = go.AddComponent<TrailRenderer>();
            tr.sharedMaterial = mat; tr.time = 0.12f; tr.minVertexDistance = 0.02f;
            tr.widthCurve = AnimationCurve.Linear(0, 0.05f, 1, 0.01f);
            tr.emitting = false;
            trails.Add((p, tr));
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(new Color(0.8f, 0.9f, 1f), 0), new GradientColorKey(new Color(0.4f, 0.55f, 1f), 1) },
                      new[] { new GradientAlphaKey(0.7f, 0), new GradientAlphaKey(0, 1) });
            tr.colorGradient = g;
        }
    }

    // the rook breaks into a run from where it stands and charges straight into the tackle (user: "初めからダッシュ")
    // at the Attack's own run-in pace: |ROOK_LUNGE| over its first 16 frames (rook_anims.py ROOK_RUN_FRAMES)
    IEnumerator RookCharge(Vector3 to)
    {
        const float run = 0.5f * 0.7f / 0.34f / (16 / 24f);
        white.Play("Charge", 0.15f);
        float dustT = 0;
        while ((to - white.transform.position).magnitude > 1e-3f)
        {
            white.transform.position = Vector3.MoveTowards(white.transform.position, to, run * Time.deltaTime);
            if ((dustT += Time.deltaTime) > 0.33f) { dustT = 0; Dust(white.transform.position, 0.8f); }
            yield return null;
        }
    }

    // the queen (queen_anims.py): Chant, 光の裁き (Skill: the pawn is driven to its knees), 女王の審判 (Ultimate: it dies)
    const int QChantCircle = 26, QPillars = 40, QBurst = 60, QPierce = 46;
    IEnumerator QueenSpell()
    {
        var gold = new Color(1f, 0.94f, 0.78f);
        float d = white.Play("Chant", 0.15f);
        yield return new WaitForSeconds(QChantCircle / 24f);
        StartCoroutine(Magic(white.transform.position, d - QChantCircle / 24f));
        yield return new WaitForSeconds(d - QChantCircle / 24f - 0.1f);
        d = white.Play("Skill", 0.15f);
        yield return new WaitForSeconds(QPillars / 24f);
        StartCoroutine(Ring(black.transform.position + Vector3.up * 0.03f, gold, 1.6f, 0.6f, false, -0.7f));
        yield return new WaitForSeconds((QBurst - 16 - QPillars) / 24f);
        black.Play("Hit", 0.12f);
        yield return new WaitForSeconds(16 / 24f);
        Spark(black.transform.position + Vector3.up * 0.75f); StartCoroutine(ShockWave(black.transform.position)); shake = 0.1f;
        Sfx("magic_burst", black.transform.position + Vector3.up * 0.75f, 0.85f, 0.02f);
        yield return new WaitForSeconds(d - QBurst / 24f - 0.2f);
        d = white.Play("Ultimate", 0.15f);
        Sfx("magic_charge", white.transform.position + Vector3.up * 1f, 0.9f, 0.02f);
        StartCoroutine(Ring(white.transform.position + Vector3.up * 0.03f, new Color(0.79f, 0.65f, 1f), 3f, 1.4f, false, 0.3f));
        yield return new WaitForSeconds((QPierce - 16) / 24f);
        float dd = black.Play("Death", 0.12f);
        var dying = StartCoroutine(DieCrumbling(black, dd * 0.75f, 0.29f));
        yield return new WaitForSeconds(16 / 24f);
        var at = black.transform.position + Vector3.up * 0.72f;
        Spark(at); Spark(at); StartCoroutine(ShockWave(black.transform.position)); shake = 0.14f;
        Sfx("magic_burst", at, 1f, 0.02f);
        yield return new WaitForSeconds(d - QPierce / 24f);
        white.Play("Victory");
        yield return dying;
        yield return new WaitForSeconds(2.5f);
    }

    // the piece's first blow is caught on the pawn's crossed daggers (cutLen: board units along the piece's blade)
    IEnumerator PieceBlocked(float cutLen)
    {
        float d = Mathf.Max(white.Play("AttackBlocked", 0.15f), black.Play("Block", 0.15f));
        yield return new WaitForSeconds(HitTime);
        GuardFlash(white.Bone("weapon").TransformPoint(0, cutLen, 0), new Color(0.8f, 0.9f, 1f));
        Dust(white.transform.position, 0.8f);
        yield return new WaitForSeconds(d - HitTime - 0.12f);
    }

    // the pawn answers - leaping in as far as it must (extra squares) - and the piece turns it aside (Block)
    IEnumerator PawnCounter(float extra)
    {
        float d = Mathf.Max(black.Play("AttackBlocked", 0.15f), white.Play("Block", 0.15f));
        var basePos = black.transform.position; var dir = black.transform.forward;
        for (float t = 0; t < d - 0.12f; t += Time.deltaTime)
        {
            float f = t * 24f;
            float k = f < 16 ? Mathf.Sin(Mathf.Clamp01((f - 3) / 13f) * Mathf.PI / 2) : Mathf.Clamp01(1 - (f - 22) / 14f);
            black.transform.position = basePos + dir * extra * k;
            if (f >= 16 && f - Time.deltaTime * 24f < 16)
            {
                GuardFlash(black.Bone("weapon").TransformPoint(0, Cut, 0), new Color(0.8f, 0.9f, 1f));
                Dust(black.transform.position, 0.6f);
            }
            yield return null;
        }
        black.transform.position = basePos;
        black.Play("Ready", 0.2f); white.Play("Idle", 0.2f);
        yield return new WaitForSeconds(0.25f);
    }

    // a blow stopped by a blade: sparks and a bright ring bursting out, facing the camera
    public void GuardFlash(Vector3 at, Color c)
    {
        Spark(at); shake = Mathf.Max(shake, 0.03f);
        Sfx("clash", at, 1f, 0.05f);
        StartCoroutine(Ring(at, c, 0.32f, 0.3f, true));
    }

    public IEnumerator Ring(Vector3 at, Color c, float life, float radius, bool faceCamera, float spin = 0)
    {
        var lr = new GameObject("Ring").AddComponent<LineRenderer>();
        lr.sharedMaterial = new Material(Shader.Find("Legacy Shaders/Particles/Additive"));
        lr.positionCount = 40; lr.loop = true; lr.widthMultiplier = 0.02f; lr.useWorldSpace = true;
        for (float t = 0; t < life; t += Time.deltaTime)
        {
            float u = t / life, r = 0.03f + radius * Mathf.Sqrt(faceCamera ? u : Mathf.Min(1, u * 4));
            var cam = Camera.main ? Camera.main.transform : null;
            Vector3 ax = faceCamera && cam ? cam.right : Vector3.right, ay = faceCamera && cam ? cam.up : Vector3.forward;
            for (int i = 0; i < 40; i++)
            {
                float a = i / 40f * Mathf.PI * 2 + spin * t;
                lr.SetPosition(i, at + (ax * Mathf.Cos(a) + ay * Mathf.Sin(a)) * r);
            }
            float alpha = faceCamera ? 1 - u : Mathf.Min(1, u * 5) * (u > 0.85f ? (1 - u) / 0.15f : 1);
            lr.startColor = lr.endColor = new Color(c.r, c.g, c.b, alpha);
            yield return null;
        }
        Destroy(lr.sharedMaterial); Destroy(lr.gameObject);
    }

    // dust kicked off the board (footfalls, lunges, landings)
    ParticleSystem dust;
    public void Dust(Vector3 at, float size)
    {
        if (!dust)
        {
            var go = new GameObject("Dust"); dust = go.AddComponent<ParticleSystem>(); dust.Stop();
            var m = dust.main; m.playOnAwake = false; m.loop = false; m.startLifetime = new ParticleSystem.MinMaxCurve(0.6f, 1f);
            m.startSpeed = new ParticleSystem.MinMaxCurve(0.1f, 0.35f); m.startSize = new ParticleSystem.MinMaxCurve(0.08f, 0.18f);
            m.startColor = new Color(0.72f, 0.67f, 0.59f, 0.35f); m.simulationSpace = ParticleSystemSimulationSpace.World; m.gravityModifier = -0.02f;
            var em = dust.emission; em.rateOverTime = 0;
            var sh = dust.shape; sh.shapeType = ParticleSystemShapeType.Circle; sh.radius = 0.12f; sh.rotation = new Vector3(-90, 0, 0);
            var sz = dust.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, 0.4f, 1, 1.6f));
            var col = dust.colorOverLifetime; col.enabled = true;
            var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                                              new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0, 1) });
            col.color = g;
            go.GetComponent<ParticleSystemRenderer>().sharedMaterial = new Material(Shader.Find("Legacy Shaders/Particles/Alpha Blended"));
        }
        dust.transform.position = new Vector3(at.x, 0.04f, at.z);
        dust.Emit(Mathf.RoundToInt(6 * size));
        Sfx("thud", at, Mathf.Clamp01(0.25f + 0.25f * size), 0.1f);   // footfalls, stamps and landings
    }

    // the queen's spell: violet circles open on the board under her, then she strikes
    public IEnumerator Magic(Vector3 at, float seconds)
    {
        var c = new Color(0.65f, 0.48f, 1f);
        Sfx("magic_charge", at + Vector3.up * 0.8f, 0.8f, 0.02f);
        StartCoroutine(Ring(at + Vector3.up * 0.03f, c, seconds + 0.2f, 0.55f, false, 0.8f));
        StartCoroutine(Ring(at + Vector3.up * 0.035f, c, seconds + 0.2f, 0.34f, false, -1.4f));
        var light = new GameObject("MagicLight").AddComponent<Light>();
        light.type = LightType.Point; light.color = c; light.range = 3; light.transform.position = at + Vector3.up * 0.6f;
        for (float t = 0; t < seconds; t += Time.deltaTime) { light.intensity = 4 * Mathf.Sin(t / seconds * Mathf.PI); yield return null; }
        Destroy(light.gameObject);
    }

    // the pawns wear their daggers sheathed; a defender draws them while the attacker approaches
    IEnumerator DrawLater(ChessPiece p, float delay)
    {
        yield return new WaitForSeconds(delay);
        float d = p.Play("Draw", 0.1f);
        StartCoroutine(SfxLater("draw", p.transform.position + Vector3.up * 0.6f, 0.3f, 0.7f));
        yield return new WaitForSeconds(d);
        if (p.gameObject.activeSelf && p.IsPlaying("Draw")) p.Play("Ready");
    }

    // storyboard row 3: the orb gathers light, a crackling bolt leaves it on frame BoltFrame and strikes
    const int BoltFrame = 22, BoltFlight = 4;   // BlenderSource/bishop_anims.py
    IEnumerator BishopCast(bool blocked)
    {
        var orb = white.Bone("orb");
        var orbMat = white.MainRenderer.sharedMaterials.Length > 3 ? white.MainRenderer.materials[3] : null;
        Color baseGlow = orbMat ? orbMat.GetColor("_EmissionColor") : Color.black;
        float d = white.Play("Attack");
        float t = 0, deathAt = (BoltFrame + BoltFlight - 16) / 24f;   // the pawn's Death takes the blow on its frame 16
        Coroutine dying = null;
        bool blockStarted = false;
        while (t < BoltFrame / 24f)
        {
            if (orbMat) orbMat.SetColor("_EmissionColor", baseGlow * (1 + 5 * Mathf.Pow(t / (BoltFrame / 24f), 2)));
            if (dying == null && !blockStarted && t >= deathAt)
            {
                if (blocked) { black.Play("Block", 0.12f); blockStarted = true; }
                else { float dd = black.Play("Death"); dying = StartCoroutine(DieCrumbling(black, dd * 0.75f, 0.29f)); }
            }
            t += Time.deltaTime;
            yield return null;
        }
        if (orbMat) orbMat.SetColor("_EmissionColor", baseGlow);
        var to = blocked ? ShieldFace(black, white) : black.transform.position + Vector3.up * 0.68f;
        StartCoroutine(Lightning(orb.position, to, BoltFlight / 24f));   // the impact lands with the bolt, not after its glow
        yield return new WaitForSeconds(BoltFlight / 24f);
        if (blocked)
        {
            GuardFlash(to, new Color(0.75f, 0.88f, 1f));
            yield return new WaitForSeconds(d - (BoltFrame + BoltFlight) / 24f + 0.28f);
            white.Play("Idle", 0.2f); black.Play("Ready", 0.2f);
            yield return new WaitForSeconds(0.5f);
            yield break;
        }
        Spark(to); shake = 0.05f; Sfx("hit", to, 0.8f);
        yield return new WaitForSeconds(d - (BoltFrame + BoltFlight) / 24f + 0.3f);
        white.Play("Victory");
        yield return dying;
        yield return new WaitForSeconds(2.5f);
    }

    public IEnumerator Lightning(Vector3 from, Vector3 to, float flight)
    {
        var lines = new LineRenderer[3];
        var mat = new Material(Shader.Find("Legacy Shaders/Particles/Additive"));
        Sfx("lightning", Vector3.Lerp(from, to, 0.5f), 0.9f, 0.05f);
        for (int k = 0; k < lines.Length; k++)
        {
            var lr = new GameObject("Bolt").AddComponent<LineRenderer>();
            lr.sharedMaterial = mat; lr.positionCount = 15; lr.widthMultiplier = k == 0 ? 0.025f : 0.012f;
            lr.startColor = lr.endColor = new Color(0.75f, 0.88f, 1f);
            lines[k] = lr;
        }
        var flash = new GameObject("BoltLight").AddComponent<Light>();
        flash.type = LightType.Point; flash.color = new Color(0.55f, 0.72f, 1f); flash.range = 4;
        for (float t = 0, life = flight + 0.38f; t < life; t += Time.deltaTime)
        {
            float u = Mathf.Min(1, t / flight), fade = 1 - Mathf.Max(0, (t - flight) / 0.38f);
            var head = Vector3.Lerp(from, to, u);
            foreach (var lr in lines)   // re-jag every frame so it crackles
            {
                for (int i = 0; i < 15; i++)
                    lr.SetPosition(i, Vector3.Lerp(from, head, i / 14f) + (i > 0 && i < 14 ? Random.insideUnitSphere * 0.05f : Vector3.zero));
                var c = new Color(0.75f, 0.88f, 1f, fade); lr.startColor = lr.endColor = c;
            }
            flash.transform.position = head; flash.intensity = 4 * fade;
            yield return null;
        }
        foreach (var lr in lines) Destroy(lr.gameObject);
        Destroy(flash.gameObject); Destroy(mat);
    }

    IEnumerator KnightCharge()
    {
        // the pawn crosses its daggers as the horse surges; the lance beats it aside and reaches the body
        float d = white.Play("Attack");
        float dd = black.Play("Death");
        var dying = StartCoroutine(DieCrumbling(black, dd * 0.75f, 0.29f));
        yield return new WaitForSeconds(HitTime);   // the lance lands on frame 16
        var at = black.transform.position + Vector3.up * 0.68f;
        Spark(at); shake = 0.06f; Sfx("hit", at, 1f); Sfx("clash", at, 0.5f);
        Color tint = black.MainRenderer.sharedMaterial.GetColor("_Color");
        for (int i = 0; i < 14; i++) Chunk(at, 0.018f, 2.2f, tint);   // stone chips spray from the blow
        if (matchup == Matchup.KingVsPawn)
        {
            yield return new WaitForSeconds((KingSlamFrame - 16) / 24f);
            var bite = white.transform.position + white.transform.forward * 1.0f;
            StartCoroutine(ShockWave(bite)); shake = 0.2f;
            for (int i = 0; i < 18; i++) Chunk(bite + Vector3.up * 0.05f, 0.02f, 2.6f, tint);
            yield return new WaitForSeconds(d - KingSlamFrame / 24f);
        }
        else yield return new WaitForSeconds(d - HitTime);
        if (matchup == Matchup.RookVsPawn) white.transform.position += white.transform.forward * 1.24f;   // the tackle ends where it hit
        yield return new WaitForSeconds(0.2f);
        white.Play("Victory", matchup == Matchup.RookVsPawn ? 0f : 0.2f);
        yield return dying;
        yield return new WaitForSeconds(2.5f);
    }

    const int KingSlamFrame = 19;   // BlenderSource/king_anims.py KING_SLAM_FRAME
    // two flat gold rings racing out over the board + a warm flash (cheap: line renderers, no post effects)
    // the bishop's grand spell (storyboard "魔法発動シーン"; bishop_anims.py SPELL_FRAME / SPELL_FLIGHT): power gathers in
    // a growing orb at the staff, rune circles open on the board in two stages, the shot of light flies trailing
    // rings and bursts on the pawn
    const int SpellFrame = 48, SpellFlight = 8;
    IEnumerator BishopSpell()
    {
        var orb = white.Bone("orb");
        var blue = new Color(0.62f, 0.75f, 1f);
        float d = white.Play("Spell", 0.15f);
        StartCoroutine(SfxLater("magic_charge", white.transform.position + Vector3.up * 1.2f, 0.25f, 0.9f));
        var core = GameObject.CreatePrimitive(PrimitiveType.Sphere); Destroy(core.GetComponent<Collider>());
        var coreMat = new Material(Shader.Find("Legacy Shaders/Particles/Additive")); coreMat.SetColor("_TintColor", new Color(0.8f, 0.9f, 1f, 0.9f));
        core.GetComponent<Renderer>().sharedMaterial = coreMat;
        var glow = new GameObject("SpellLight").AddComponent<Light>(); glow.type = LightType.Point; glow.color = blue; glow.range = 4;
        Coroutine dying = null; int stage = 0;
        for (float t = 0; t < SpellFrame / 24f; t += Time.deltaTime)
        {
            float f = t * 24, k = Mathf.Min(1, f / 40f);
            core.transform.position = orb.position; core.transform.localScale = Vector3.one * (0.03f + 0.14f * k * k);
            glow.transform.position = orb.position; glow.intensity = 1 + 6 * k;
            if (stage == 0 && f >= 20) { stage = 1; StartCoroutine(Ring(white.transform.position + Vector3.up * 0.03f, blue, 2.4f, 0.55f, false, 0.6f)); }
            if (stage == 1 && f >= 30)
            {
                stage = 2;
                StartCoroutine(Ring(white.transform.position + Vector3.up * 0.035f, blue, 1.9f, 0.95f, false, -0.4f));
                StartCoroutine(Ring(white.transform.position + Vector3.up * 0.04f, new Color(0.8f, 0.88f, 1f), 1.9f, 0.3f, false, 1.5f));
            }
            if (dying == null && f >= SpellFrame + SpellFlight - 16)   // the pawn's Death takes the blow on its frame 16
            { float dd = black.Play("Death"); dying = StartCoroutine(DieCrumbling(black, dd * 0.75f, 0.29f)); }
            yield return null;
        }
        var from = orb.position; var to = black.transform.position + Vector3.up * 0.68f;
        int lastRing = -1;
        for (float t = 0; t < SpellFlight / 24f; t += Time.deltaTime)
        {
            float u = t / (SpellFlight / 24f);
            core.transform.position = Vector3.Lerp(from, to, u); core.transform.localScale = Vector3.one * 0.16f;
            glow.transform.position = core.transform.position;
            if (dying == null && t * 24 + SpellFrame >= SpellFrame + SpellFlight - 16)
            { float dd = black.Play("Death"); dying = StartCoroutine(DieCrumbling(black, dd * 0.75f, 0.29f)); }
            int ring = Mathf.FloorToInt(u * 5);
            if (ring != lastRing) { lastRing = ring; StartCoroutine(Ring(core.transform.position, blue, 0.5f, 0.12f, true)); }
            yield return null;
        }
        Destroy(core); Destroy(coreMat); Destroy(glow.gameObject);
        Spark(to); Spark(to); shake = 0.12f;
        Sfx("magic_burst", to, 1f, 0.02f);
        StartCoroutine(ShockWave(new Vector3(to.x, 0, to.z)));
        Dust(to, 1.6f);
        Color tint = black.MainRenderer.sharedMaterial.GetColor("_Color");
        for (int i = 0; i < 14; i++) Chunk(to, 0.018f, 2.2f, tint);
        yield return new WaitForSeconds(Mathf.Max(0, d - (SpellFrame + SpellFlight) / 24f) + 0.2f);
        white.Play("Victory");
        if (dying != null) yield return dying;
        yield return new WaitForSeconds(2.5f);
    }

    public IEnumerator ShockWave(Vector3 at)
    {
        var mat = new Material(Shader.Find("Legacy Shaders/Particles/Additive"));
        var rings = new LineRenderer[2];
        for (int k = 0; k < 2; k++)
        {
            var lr = new GameObject("ShockWave").AddComponent<LineRenderer>();
            lr.sharedMaterial = mat; lr.positionCount = 48; lr.loop = true; lr.widthMultiplier = 0.06f - k * 0.03f;
            rings[k] = lr;
        }
        var flash = new GameObject("WaveLight").AddComponent<Light>();
        flash.type = LightType.Point; flash.color = new Color(1f, 0.78f, 0.38f); flash.range = 4;
        flash.transform.position = at + Vector3.up * 0.5f;
        Sfx("shockwave", at, 0.9f, 0.04f);
        const float life = 0.9f;
        for (float t = 0; t < life + 0.12f; t += Time.deltaTime)
        {
            for (int k = 0; k < 2; k++)
            {
                float u = Mathf.Clamp01((t - k * 0.12f) / life), r = 0.02f + 2.6f * Mathf.Sqrt(u);
                for (int i = 0; i < 48; i++)
                {
                    float a = i / 48f * Mathf.PI * 2;
                    rings[k].SetPosition(i, at + new Vector3(Mathf.Cos(a) * r, 0.02f, Mathf.Sin(a) * r));
                }
                var c = new Color(1f, 0.82f, 0.48f, u <= 0 ? 0 : (1 - u) * 0.9f); rings[k].startColor = rings[k].endColor = c;
            }
            flash.intensity = 6 * Mathf.Max(0, 1 - t / 0.4f);
            yield return null;
        }
        foreach (var lr in rings) Destroy(lr.gameObject);
        Destroy(flash.gameObject); Destroy(mat);
    }

    // ---- sound (procedural clips from SoundSource/sfx.py): a small pool of 3D voices placed at each event, plus the
    //      crowd in the stands as a 2D loop that swells on a kill
    readonly Dictionary<string, List<AudioClip>> sfx = new Dictionary<string, List<AudioClip>>();
    AudioSource[] voices;
    int nextVoice;
    AudioSource crowd;

    void InitAudio()
    {
        if (!soundOn) return;
        foreach (var c in sfxClips ?? new AudioClip[0])
        {
            if (!c) continue;
            var key = System.Text.RegularExpressions.Regex.Replace(c.name, @"_\d+$", "");
            if (!sfx.TryGetValue(key, out var list)) sfx[key] = list = new List<AudioClip>();
            list.Add(c);
        }
        voices = new AudioSource[12];
        for (int i = 0; i < voices.Length; i++)
        {
            var a = new GameObject("Sfx Voice").AddComponent<AudioSource>();
            a.transform.SetParent(transform, false);
            a.playOnAwake = false; a.spatialBlend = 0.7f; a.minDistance = 3f; a.maxDistance = 30f; a.rolloffMode = AudioRolloffMode.Logarithmic;
            voices[i] = a;
        }
        if (sfx.TryGetValue("crowd_loop", out var cl))
        {
            crowd = gameObject.AddComponent<AudioSource>();
            crowd.clip = cl[0]; crowd.loop = true; crowd.spatialBlend = 0; crowd.volume = 0.32f; crowd.Play();
        }
    }

    // vol: 0..1; pitch is jittered so repeated hits never sound identical
    public void Sfx(string name, Vector3 at, float vol = 1f, float pitchJitter = 0.06f)
    {
        if (voices == null || !sfx.TryGetValue(name, out var list)) return;
        var a = voices[nextVoice++ % voices.Length];
        a.transform.position = at;
        a.clip = list[Random.Range(0, list.Count)];
        a.volume = vol; a.pitch = 1 + Random.Range(-pitchJitter, pitchJitter);
        a.Play();
    }

    // the stands roar at a kill and settle back to their murmur
    IEnumerator Cheer()
    {
        Sfx("crowd_cheer", transform.position + Vector3.up * 3, 0.8f, 0.03f);
        if (!crowd) yield break;
        for (float t = 0; t < 4f; t += Time.deltaTime) { crowd.volume = 0.32f + 0.25f * Mathf.Sin(Mathf.Clamp01(t / 4f) * Mathf.PI); yield return null; }
        crowd.volume = 0.32f;
    }

    void Place()
    {
        foreach (var r in rubble) Destroy(r.t.gameObject);
        rubble.Clear();
        foreach (var p in new[] { white, black }) { p.gameObject.SetActive(true); p.SetCrumble(0); }
        white.transform.position = whiteStart;
        white.transform.rotation = Quaternion.Euler(0, 180, 0);
        black.transform.position = blackSpot;
    }

    // where the attacker's point lands: the X of the defender's crossed daggers (a little above the two fists)
    static Vector3 ShieldFace(ChessPiece defender, ChessPiece attacker)
    {
        var s = (defender.Bone("weapon").position + defender.Bone("weapon.L").position) * 0.5f + Vector3.up * 0.1f;
        return s + (attacker.transform.position - defender.transform.position).normalized * 0.06f;
    }

    public void Spark(Vector3 at)
    {
        sparks.transform.position = at;
        sparks.Emit(40);
    }

    // ---- death: the statue is eaten away while it falls, chunks drop off random limbs, the rest
    //      collapses into a heap that thins out (screen-door fade) and disappears
    public IEnumerator DieCrumbling(ChessPiece p, float dur, float start)
    {
        var heapMpb = new MaterialPropertyBlock();
        Color tint = p.MainRenderer.sharedMaterial.GetColor("_Color");
        StartCoroutine(SfxLater("crumble", p.transform.position + Vector3.up * 0.5f, dur * start, 0.9f));
        StartCoroutine(SfxLater("crumble", p.transform.position + Vector3.up * 0.2f, dur * 0.95f, 0.6f));
        StartCoroutine(CheerLater(dur * start + 0.3f));
        float t = 0, next = 0;
        while (t < dur)
        {
            float u = t / dur, c = Mathf.Max(0, (u - start) / (1 - start));
            p.SetCrumble(c * c * 0.62f);
            if (u > start && t > next)
            {
                Chunk(p.Bones[Random.Range(0, p.Bones.Length)].position, 0.03f + c * 0.03f, 0.6f, tint);
                next = t + 0.07f - c * 0.04f;
            }
            t += Time.deltaTime;
            yield return null;
        }
        foreach (var b in p.Bones)
            for (int i = 0; i < 3; i++) Chunk(b.position, 0.045f, 1f, tint);
        p.gameObject.SetActive(false);

        yield return new WaitForSeconds(1.6f);
        for (float f = 0; f < 2.2f; f += Time.deltaTime)
        {
            float u = f / 2.2f;
            foreach (var r in rubble)
            {
                r.rend.GetPropertyBlock(heapMpb); heapMpb.SetFloat("_Fade", 1 - u * u); r.rend.SetPropertyBlock(heapMpb);
            }
            yield return null;
        }
        foreach (var r in rubble) Destroy(r.t.gameObject);
        rubble.Clear();
    }

    IEnumerator SfxLater(string name, Vector3 at, float delay, float vol)
    {
        yield return new WaitForSeconds(delay);
        Sfx(name, at, vol);
    }

    IEnumerator CheerLater(float delay)
    {
        yield return new WaitForSeconds(delay);
        yield return Cheer();
    }

    public void Chunk(Vector3 at, float size, float kick, Color tint)
    {
        var go = GameObject.CreatePrimitive(Random.value < 0.5f ? PrimitiveType.Cube : PrimitiveType.Sphere);
        Destroy(go.GetComponent<Collider>());
        var r = go.GetComponent<Renderer>();
        r.sharedMaterial = stoneMaterial;
        var mpb = new MaterialPropertyBlock(); mpb.SetColor("_Color", tint); mpb.SetFloat("_WorldSpace", 1); r.SetPropertyBlock(mpb);
        float s = size * (0.5f + Random.value);
        go.transform.localScale = new Vector3(s, s * (0.6f + Random.value * 0.6f), s) * 1.6f;
        go.transform.position = at + Random.insideUnitSphere * 0.06f;
        go.transform.rotation = Random.rotation;
        rubble.Add(new Rubble
        {
            t = go.transform, rend = r, r = s * 0.8f, spin = Random.Range(-500f, 500f),
            v = new Vector3(Random.Range(-0.5f, 0.5f) * kick, Random.value * kick * 0.6f, Random.Range(-0.5f, 0.5f) * kick),
        });
    }

    void StepRubble(float dt)
    {
        foreach (var r in rubble)
        {
            var p = r.t.position;
            if (p.y <= r.r && r.v.y <= 0 && r.v.sqrMagnitude < 0.02f) { r.v = Vector3.zero; continue; }
            r.v.y -= 5.9f * dt;
            p += r.v * dt;
            r.t.Rotate(r.spin * dt, 0, 0);
            if (p.y < r.r) { p.y = r.r; r.v.y = -r.v.y * 0.25f; r.v.x *= 0.5f; r.v.z *= 0.5f; if (Mathf.Abs(r.v.y) < 0.15f) r.v.y = 0; }
            r.t.position = p;
        }
    }

    ParticleSystem MakeSparks()
    {
        var go = new GameObject("Sparks");
        var ps = go.AddComponent<ParticleSystem>();
        ps.Stop();
        var main = ps.main;
        main.playOnAwake = false; main.loop = false;
        main.startLifetime = new ParticleSystem.MinMaxCurve(0.25f, 0.6f);
        main.startSpeed = new ParticleSystem.MinMaxCurve(1.5f, 4f);
        main.startSize = new ParticleSystem.MinMaxCurve(0.012f, 0.025f);
        main.startColor = new Color(1f, 0.82f, 0.55f);
        main.gravityModifier = 0.6f;
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        var em = ps.emission; em.rateOverTime = 0;
        var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Sphere; shape.radius = 0.02f;
        var col = ps.colorOverLifetime; col.enabled = true;
        var g = new Gradient();
        g.SetKeys(new[] { new GradientColorKey(new Color(1f, 0.9f, 0.6f), 0), new GradientColorKey(new Color(1f, 0.45f, 0.1f), 1) },
                  new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0, 1) });
        col.color = g;
        var r = go.GetComponent<ParticleSystemRenderer>();
        r.renderMode = ParticleSystemRenderMode.Stretch; r.velocityScale = 0.04f; r.lengthScale = 2f;
        r.sharedMaterial = new Material(Shader.Find("Legacy Shaders/Particles/Additive"));
        return ps;
    }
}
