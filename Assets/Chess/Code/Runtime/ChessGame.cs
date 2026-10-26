using System.Collections;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using Move = ChessRules.Move;
using Flag = ChessRules.Flag;

// The playable game (user: "プレイできるようにして"): CPU or two players at one screen, no clock (user: 時間制はいらない).
// Click a piece, its legal squares light up, click one. Plain moves walk (the knight glides along its L); a capture is
// fought out with each piece's battle clip and the taken piece crumbles before the winner walks into the square.
// Effects (sparks, dust, rings, bolts, crumbling) are borrowed from PawnBattle with autoPlay off.
public class ChessGame : MonoBehaviour
{
    public ChessPiece[] templates;   // inactive: white pawn, knight, bishop, rook, queen, king, then black ones
    public PawnBattle fx;
    public Transform cameraPivot;

    enum Mode { Menu, VsCpu, TwoPlayers, Online }
    Mode mode = Mode.Menu;
    int humanSide = 1, level = 1;
    static readonly string[] LevelNames = { "やさしい", "ふつう", "つよい" };
    static readonly int[] LevelMs = { 300, 1200, 3000 }, LevelDepth = { 2, 4, 7 };

    readonly ChessRules rules = new ChessRules();
    readonly ChessPiece[] at = new ChessPiece[64];
    readonly List<ChessPiece> live = new List<ChessPiece>();
    ChessRules.Result result;
    bool busy;
    Task<Move> thinking;
    int selected = -1;
    List<Move> selMoves = new List<Move>();
    List<Move> promoChoices;
    Move? lastMove;

    // timings from the Blender clips (see PawnBattle / *_anims.py)
    const float HitTime = 16 / 24f;                       // melee blows land on frame 16; Death takes the blow on its frame 16
    const int KnTakeoff = 10, KnTouch = 34, KnHit = 30;   // knight glide (knight_anims.py)
    const float KnLandShort = 0.6f;
    const int BoltFrame = 22, BoltFlight = 4;             // bishop bolt
    const int QPierce = 46, KingSlamFrame = 19;

    // ---------------------------------------------------------------- board
    static Vector3 Pos(int s) => new Vector3(ChessRules.File(s) - 3, 0, ChessRules.Rank(s) - 3);
    static Quaternion Facing(int side) => Quaternion.Euler(0, side == 1 ? 0 : 180, 0);   // imported pieces face +Z

    readonly Renderer[] marks = new Renderer[64];
    MaterialPropertyBlock mpb;

    void Start()
    {
        mpb = new MaterialPropertyBlock();
        Input.simulateMouseWithTouches = true;   // a tap must reach IMGUI as a mouse click (mobile WebGL)
        // On a WebGL build opened on a phone, Application.isMobilePlatform is false, so detect the phone by
        // device type / touch instead and then trim the GPU cost (a colosseum full of statues is heavy on an
        // iGPU/mobile GPU) and pull the camera in, since the board sat too far away on a tall screen.
        bool phone = Application.isMobilePlatform || SystemInfo.deviceType == DeviceType.Handheld || (Input.touchSupported && Screen.width < Screen.height);
        if (phone)
        {
            QualitySettings.antiAliasing = 0;
            QualitySettings.shadows = ShadowQuality.Disable;   // biggest single GPU saving on mobile
            QualitySettings.shadowDistance = 0;
            QualitySettings.pixelLightCount = 1;
            zoom = 0.6f;   // lower zoom = closer; the board fills a phone screen instead of sitting far back
        }
        Application.targetFrameRate = 60;
        var mat = new Material(Shader.Find("Sprites/Default"));
        for (int s = 0; s < 64; s++)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Destroy(q.GetComponent<Collider>());
            q.name = "Mark " + ChessRules.Sq(s);
            q.transform.SetParent(transform, false);
            q.transform.position = Pos(s) + Vector3.up * 0.006f;
            q.transform.rotation = Quaternion.Euler(90, 0, 0);
            q.transform.localScale = Vector3.one * 0.92f;
            var r = q.GetComponent<Renderer>();
            r.sharedMaterial = mat; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            r.enabled = false;
            marks[s] = r;
        }
        NewGame();
    }

    void NewGame()
    {
        StopAllCoroutines();
        netResult = ""; netSending = false; netFetching = false;
        busy = false; thinking = null; selected = -1; promoChoices = null; lastMove = null;
        rules.Reset();
        result = ChessRules.Result.Playing;
        if (fx) fx.ClearTrails();
        foreach (var p in live) if (p) Destroy(p.gameObject);
        live.Clear();
        System.Array.Clear(at, 0, 64);
        for (int s = 0; s < 64; s++) if (rules.b[s] != 0) at[s] = Spawn(rules.b[s], s);
        RefreshMarks();
    }

    ChessPiece Spawn(int piece, int s)
    {
        int side = piece > 0 ? 1 : -1, type = Mathf.Abs(piece);
        var t = templates[(side == 1 ? 0 : 6) + type - 1];
        var go = Instantiate(t.gameObject, Pos(s), Facing(side));
        go.name = (side == 1 ? "White " : "Black ") + t.name.Split(' ')[1] + " " + ChessRules.Sq(s);
        go.SetActive(true);
        var p = go.GetComponent<ChessPiece>();
        // a tap target on the piece itself, so tapping the (tall) model selects the piece rather than the
        // board square behind it. Kinematic body + trigger capsule: cheap to move with the animation, hit by raycasts.
        var rb = go.AddComponent<Rigidbody>(); rb.isKinematic = true; rb.useGravity = false;
        var col = go.AddComponent<CapsuleCollider>(); col.isTrigger = true;
        col.center = new Vector3(0, 0.75f, 0); col.height = 1.7f; col.radius = 0.4f;
        live.Add(p);
        if (fx)
        {
            float along = type == ChessRules.Pawn ? 0.3f : type == ChessRules.Knight ? 1.1f : type == ChessRules.Queen ? 0.9f
                        : type == ChessRules.King ? 0.85f : type == ChessRules.Rook ? 0.8f : 0;
            if (along > 0) fx.AddTrails(p, along);
        }
        p.Play("Idle", 0);
        return p;
    }

    // ---------------------------------------------------------------- turn flow
    bool CpuTurn => mode == Mode.VsCpu && rules.side != humanSide;
    // online: the server holds the game; this board only shows it and sends this player's moves
    bool MyOnlineTurn => mode != Mode.Online || (netJoined && !netSending && rules.side == humanSide);

    void Update()
    {
        CameraControl();
        if (mode == Mode.Online) OnlinePoll();
        if (mode == Mode.Menu || busy || result != ChessRules.Result.Playing || !string.IsNullOrEmpty(netResult)) return;
        if (CpuTurn)
        {
            if (thinking == null)
            {
                var snap = rules.Clone();
                int ms = LevelMs[level], depth = LevelDepth[level];
#if UNITY_WEBGL && !UNITY_EDITOR
                // browsers give Unity no threads: think here, with a shorter budget so the pause stays brief
                thinking = Task.FromResult(ChessAI.Think(snap, Mathf.Min(ms, 1500), depth, new System.Random()));
#else
                thinking = Task.Run(() => ChessAI.Think(snap, ms, depth, new System.Random()));
#endif
            }
            else if (thinking.IsCompleted)
            {
                var m = thinking.Result; thinking = null;
                StartCoroutine(PlayMove(m));
            }
            return;
        }
        if (promoChoices != null || !MyOnlineTurn) return;
        if (Input.touchCount > 1) return;   // two fingers move the camera, never a piece
        if (Input.GetMouseButtonDown(0) && !OverHud(Input.mousePosition)) Click();   // a tap arrives as a click
    }

    void Click()
    {
        var cam = Camera.main;
        if (cam == null) return;
        var ray = cam.ScreenPointToRay(Input.mousePosition);

        // 1) tapped a piece model? pick the nearest piece the ray passes through (reliable for tall pieces)
        int s = -1;
        float best = float.MaxValue;
        foreach (var h in Physics.RaycastAll(ray, 200f))
        {
            var cp = h.collider.GetComponentInParent<ChessPiece>();
            if (cp == null || h.distance >= best) continue;
            int sq = SquareOf(cp);
            if (sq >= 0) { best = h.distance; s = sq; }
        }
        // 2) otherwise the empty board square under the tap (to move onto a highlighted square)
        if (s < 0)
        {
            if (Mathf.Abs(ray.direction.y) < 1e-4f) return;
            float k = -ray.origin.y / ray.direction.y;
            if (k < 0) return;
            var p = ray.origin + ray.direction * k;
            int f = Mathf.RoundToInt(p.x + 3), r = Mathf.RoundToInt(p.z + 3);
            if (f < 0 || f > 7 || r < 0 || r > 7) { Select(-1); return; }
            s = r * 8 + f;
        }

        if (rules.b[s] * rules.side > 0) { Select(s); return; }   // tapped own piece -> select & show its moves
        if (selected < 0) return;
        var options = selMoves.FindAll(m => m.to == s);
        if (options.Count == 0) { Select(-1); return; }
        if (options.Count > 1) { promoChoices = options; return; }   // a promotion: the player picks the piece
        Commit(options[0]);
    }

    int SquareOf(ChessPiece cp)
    {
        for (int i = 0; i < 64; i++) if (at[i] == cp) return i;
        return -1;
    }

    void Select(int s)
    {
        selected = s;
        selMoves = s < 0 ? new List<Move>() : rules.Legal().FindAll(m => m.from == s);
        RefreshMarks();
    }

    IEnumerator PlayMove(Move m)
    {
        busy = true; promoChoices = null;
        selected = -1; selMoves.Clear(); RefreshMarks();
        int side = rules.side, from = m.from, to = m.to;
        int type = Mathf.Abs(rules.b[from]);
        var mover = at[from];
        ChessPiece victim = null;
        if (m.Is(Flag.Capture)) { int vs = m.Is(Flag.EnPassant) ? to - side * 8 : to; victim = at[vs]; at[vs] = null; }
        ChessPiece rook = null; int rookTo = -1;
        if (m.Is(Flag.Castle))
        {
            int rf = to > from ? to + 1 : to - 2; rookTo = to > from ? to - 1 : to + 1;
            rook = at[rf]; at[rf] = null; at[rookTo] = rook;
        }
        at[from] = null; at[to] = mover;
        rules.Make(m); lastMove = m;
        RefreshMarks(false);

        if (victim) yield return Capture(type, mover, victim, to, side);
        else if (type == ChessRules.Knight) yield return Glide(mover, to, side);
        else if (rook) { var k = StartCoroutine(Walk(mover, to, side)); yield return Walk(rook, rookTo, side); yield return k; }
        else yield return Walk(mover, to, side);

        if (m.Is(Flag.Promo)) yield return Promote(to, m.promo);
        result = rules.Status();
        RefreshMarks();
        if (result != ChessRules.Result.Playing) yield return GameOver();
        busy = false;
    }

    // ---------------------------------------------------------------- motion
    IEnumerator TurnTo(ChessPiece p, Vector3 dir, float dur = 0.25f)
    {
        dir.y = 0; if (dir.sqrMagnitude < 1e-6f) yield break;
        var a = p.transform.rotation; var b = Quaternion.LookRotation(dir);
        for (float t = 0; t < dur; t += Time.deltaTime) { p.transform.rotation = Quaternion.Slerp(a, b, t / dur); yield return null; }
        p.transform.rotation = b;
    }

    IEnumerator Walk(ChessPiece p, int to, int side)
    {
        var target = Pos(to);
        var d = target - p.transform.position; d.y = 0;
        if (d.magnitude > 0.02f)
        {
            yield return TurnTo(p, d);
            yield return p.WalkTo(target, Mathf.Clamp(d.magnitude / 1.4f, 1f, 2.6f));   // long walks hurry
        }
        p.transform.position = target;
        p.Play("Idle", 0.25f);
        yield return TurnTo(p, Facing(side) * Vector3.forward, 0.3f);
    }

    // the knight glides along its L to the square (knight_anims.py Leap: height and pitch in the clip)
    IEnumerator Glide(ChessPiece p, int to, int side)
    {
        var start = p.transform.position; var target = Pos(to);
        yield return TurnTo(p, target - start, 0.2f);
        float d = p.Play("Leap", 0.1f);
        for (float t = 0; t < d; t += Time.deltaTime)
        {
            float f = t * 24f;
            p.transform.position = Vector3.Lerp(start, target, Mathf.Clamp01((f - KnTakeoff) / (KnTouch - KnTakeoff)));
            yield return null;
        }
        p.transform.position = target;
        fx.Dust(target, 1.2f);
        p.Play("Idle", 0.25f);
        yield return TurnTo(p, Facing(side) * Vector3.forward, 0.3f);
    }

    // stand off at the distance a piece's killing clip was made for (closing in, or stepping back for a run-up)
    IEnumerator Approach(ChessPiece a, Vector3 victimPos, float reach, bool run = false)
    {
        var d = victimPos - a.transform.position; d.y = 0;
        float dist = d.magnitude;
        yield return TurnTo(a, d);
        var spot = victimPos - d.normalized * reach;
        if (dist > reach + 0.03f)
        {
            if (run)   // the rook breaks into its run straight away (PawnBattle.RookCharge)
            {
                const float speed = 0.5f * 0.7f / 0.34f / (16 / 24f);
                a.Play("Charge", 0.15f);
                float dustT = 0;
                while ((spot - a.transform.position).magnitude > 1e-3f)
                {
                    a.transform.position = Vector3.MoveTowards(a.transform.position, spot, speed * Time.deltaTime);
                    if ((dustT += Time.deltaTime) > 0.33f) { dustT = 0; fx.Dust(a.transform.position, 0.8f); }
                    yield return null;
                }
            }
            else yield return a.WalkTo(spot, Mathf.Clamp((dist - reach) / 1.4f, 1f, 2.6f));
        }
        else if (dist < reach - 0.03f)
        {
            var from = a.transform.position;
            a.Play("Idle", 0.15f);
            for (float t = 0; t < 0.35f; t += Time.deltaTime) { a.transform.position = Vector3.Lerp(from, spot, Mathf.SmoothStep(0, 1, t / 0.35f)); yield return null; }
            a.transform.position = spot;
        }
    }

    // ---------------------------------------------------------------- captures
    Vector3 Chest(ChessPiece p)
    {
        var b = p.MainRenderer.bounds;
        return new Vector3(p.transform.position.x, b.center.y + b.extents.y * 0.15f, p.transform.position.z);
    }

    void Blow(ChessPiece victim, Vector3 at, float shake)
    {
        fx.Spark(at); fx.shake = shake;
        Color tint = victim.MainRenderer.sharedMaterial.GetColor("_Color");
        for (int i = 0; i < 14; i++) fx.Chunk(at, 0.018f, 2.2f, tint);
    }

    Coroutine Die(ChessPiece v)
    {
        float dd = v.Play("Death", 0.1f);
        return StartCoroutine(fx.DieCrumbling(v, dd * 0.75f, 0.29f));
    }

    IEnumerator Capture(int type, ChessPiece a, ChessPiece v, int to, int side)
    {
        var vp = v.transform.position;
        StartCoroutine(TurnTo(v, a.transform.position - vp, 0.3f));   // the defender turns to meet it
        switch (type)
        {
            case ChessRules.Pawn:
            {
                float dr = a.Play("Draw", 0.1f); yield return new WaitForSeconds(dr * 0.85f);
                a.Play("Ready", 0.15f);
                yield return Approach(a, vp, 1.0f);
                float d = a.Play("Attack", 0.1f); Die(v);
                yield return new WaitForSeconds(HitTime); Blow(v, Chest(v), 0.06f);
                yield return new WaitForSeconds(d - HitTime);
                break;
            }
            case ChessRules.Knight:   // glides along its L and spears the piece on the way down (user's design)
            {
                float dr = a.Play("Draw", 0.15f); yield return new WaitForSeconds(dr);
                var start = a.transform.position;
                var dir = (vp - start); dir.y = 0;
                var land = start + dir.normalized * Mathf.Max(0, dir.magnitude - KnLandShort);
                yield return TurnTo(a, dir, 0.2f);
                float d = a.Play("LeapAttack", 0.1f);
                bool dying = false, hit = false;
                for (float t = 0; t < d; t += Time.deltaTime)
                {
                    float f = t * 24f;
                    a.transform.position = Vector3.Lerp(start, land, Mathf.Clamp01((f - KnTakeoff) / (KnTouch - KnTakeoff)));
                    if (!dying && f >= KnHit - 16) { dying = true; Die(v); }
                    if (!hit && f >= KnHit) { hit = true; Blow(v, Chest(v), 0.08f); }
                    yield return null;
                }
                a.transform.position = land;
                break;
            }
            case ChessRules.Bishop:   // a bolt from the orb at two squares
            {
                yield return Approach(a, vp, 2.2f);
                float d = a.Play("Attack", 0.15f);
                float deathAt = (BoltFrame + BoltFlight - 16) / 24f;
                yield return new WaitForSeconds(deathAt); Die(v);
                yield return new WaitForSeconds(BoltFrame / 24f - deathAt);
                var to3 = Chest(v);
                // the impact lands with the bolt (frame 26 = the victim's Death frame 16), not after its glow fades
                StartCoroutine(fx.Lightning(a.Bone("orb").position, to3, BoltFlight / 24f));
                yield return new WaitForSeconds(BoltFlight / 24f);
                Blow(v, to3, 0.05f);
                yield return new WaitForSeconds(Mathf.Max(0, d - (BoltFrame + BoltFlight) / 24f));
                break;
            }
            case ChessRules.Rook:   // runs in and shoulders through it with the shield
            {
                yield return Approach(a, vp, 1.6f, true);
                float d = a.Play("Attack", 0.1f); Die(v);
                yield return new WaitForSeconds(HitTime); Blow(v, Chest(v), 0.08f);
                yield return new WaitForSeconds(d - HitTime);
                a.transform.position += a.transform.forward * 1.24f;   // the tackle ends where it hit (rook_anims.py)
                a.Play("Idle", 0);
                break;
            }
            case ChessRules.Queen:   // no blade: 女王の審判 (user: 派手な魔法で一掃)
            {
                yield return Approach(a, vp, 1.3f);
                float d = a.Play("Ultimate", 0.15f);
                StartCoroutine(fx.Ring(a.transform.position + Vector3.up * 0.03f, new Color(0.79f, 0.65f, 1f), 3f, 1.4f, false, 0.3f));
                yield return new WaitForSeconds((QPierce - 16) / 24f); Die(v);
                yield return new WaitForSeconds(16 / 24f);
                var c = Chest(v);
                fx.Spark(c); StartCoroutine(fx.ShockWave(new Vector3(vp.x, 0, vp.z))); Blow(v, c, 0.14f);
                yield return new WaitForSeconds(Mathf.Max(0, d - QPierce / 24f));
                break;
            }
            default:   // the king: a cleave that bites the board
            {
                yield return Approach(a, vp, 1.0f);
                float d = a.Play("Attack", 0.1f); Die(v);
                yield return new WaitForSeconds(HitTime); Blow(v, Chest(v), 0.06f);
                yield return new WaitForSeconds((KingSlamFrame - 16) / 24f);
                StartCoroutine(fx.ShockWave(a.transform.position + a.transform.forward * 1.0f)); fx.shake = 0.2f;
                yield return new WaitForSeconds(Mathf.Max(0, d - KingSlamFrame / 24f));
                break;
            }
        }
        yield return Walk(a, to, side);   // into the taken square
    }

    IEnumerator Promote(int s, int promo)
    {
        var old = at[s];
        var p = Pos(s);
        StartCoroutine(fx.Ring(p + Vector3.up * 0.03f, new Color(1f, 0.9f, 0.6f), 1.4f, 0.6f, false, 0.8f));
        fx.Spark(p + Vector3.up * 0.6f);
        yield return new WaitForSeconds(0.35f);
        old.gameObject.SetActive(false);
        at[s] = Spawn(promo, s);
        at[s].Play("Victory", 0.1f);
        yield return new WaitForSeconds(1.2f);
        at[s].Play("Idle", 0.3f);
    }

    IEnumerator GameOver()
    {
        if (result == ChessRules.Result.WhiteMates || result == ChessRules.Result.BlackMates)
        {
            int loser = result == ChessRules.Result.WhiteMates ? -1 : 1;
            var king = at[rules.KingSquare(loser)];
            var winner = at[rules.KingSquare(-loser)];
            yield return new WaitForSeconds(0.6f);
            if (king) { Die(king); }
            yield return new WaitForSeconds(1.2f);
            if (winner) winner.Play("Victory", 0.2f);
        }
    }

    // ---------------------------------------------------------------- marks
    static readonly Color CSelect = new Color(1f, 0.85f, 0.3f, 0.70f), CMove = new Color(0.35f, 1f, 0.5f, 0.60f),
                          CTake = new Color(1f, 0.3f, 0.25f, 0.70f), CLast = new Color(0.95f, 0.8f, 0.4f, 0.28f),
                          CCheck = new Color(1f, 0.1f, 0.05f, 0.7f);

    void Mark(int s, Color c)
    {
        var r = marks[s]; r.enabled = true;
        r.GetPropertyBlock(mpb); mpb.SetColor("_Color", c); r.SetPropertyBlock(mpb);
    }

    void RefreshMarks(bool showSelection = true)
    {
        if (marks[0] == null) return;
        foreach (var r in marks) r.enabled = false;
        if (lastMove.HasValue) { Mark(lastMove.Value.from, CLast); Mark(lastMove.Value.to, CLast); }
        if (rules.InCheck(rules.side)) Mark(rules.KingSquare(rules.side), CCheck);
        if (!showSelection || selected < 0) return;
        Mark(selected, CSelect);
        foreach (var m in selMoves) Mark(m.to, m.Is(Flag.Capture) ? CTake : CMove);
    }

    // ---------------------------------------------------------------- camera
    float yaw, yawOffset, zoom = 1f;
    bool watchAngle = true;   // when a move plays: true = swing to the angled battle view, false = stay overhead
    float camT;               // 0 = angled view, 1 = top-down (overhead); lerps toward the target each frame
    Camera cam;

    void CameraControl()
    {
        if (!cameraPivot) return;
        float target;
        if (mode == Mode.Menu) target = yaw + 6f * Time.deltaTime;   // a slow turn round the arena behind the menu
        else if (mode == Mode.VsCpu) target = humanSide == 1 ? 0 : 180;
        else if (mode == Mode.Online) target = humanSide == 1 ? 0 : 180;
        else target = rules.side == 1 ? 0 : 180;   // two players: the board turns to whoever is to move
        if (Input.GetMouseButton(1)) yawOffset += Input.GetAxis("Mouse X") * 4f;
        zoom = Mathf.Clamp(zoom - Input.mouseScrollDelta.y * 0.06f, 0.45f, 1.4f);
        if (Input.touchCount == 2)   // two fingers: slide sideways to turn, pinch to zoom
        {
            Touch a = Input.GetTouch(0), b = Input.GetTouch(1);
            yawOffset += (a.deltaPosition.x + b.deltaPosition.x) * 0.5f * 180f / Mathf.Max(1, Screen.width);
            float now = (a.position - b.position).magnitude, before = ((a.position - a.deltaPosition) - (b.position - b.deltaPosition)).magnitude;
            if (before > 1) zoom = Mathf.Clamp(zoom * before / Mathf.Max(1, now), 0.45f, 1.4f);
        }
        FitBoard();
        yaw = mode == Mode.Menu ? target : Mathf.LerpAngle(yaw, target + yawOffset, Time.deltaTime * 3f);
        cameraPivot.rotation = Quaternion.Euler(0, yaw, 0);
        cameraPivot.localScale = Vector3.one * zoom;

        // Overhead while choosing a move (easy to read every piece's options from straight above); during a
        // move, drop to the angled view to watch the battle only if the player chose "斜め". Menu stays angled.
        if (!cam) cam = cameraPivot.GetComponentInChildren<Camera>();
        float tTarget = mode == Mode.Menu ? 0f : (busy && watchAngle) ? 0f : 1f;
        camT = Mathf.MoveTowards(camT, tTarget, Time.deltaTime * 2.4f);
        if (cam)
        {
            var lp = Vector3.Lerp(new Vector3(0, 9.5f, -9.5f), new Vector3(0, 14f, -0.7f), camT);
            var lt = Vector3.Lerp(new Vector3(0, 0, 0.4f), Vector3.zero, camT);
            cam.transform.localPosition = lp;
            cam.transform.localRotation = Quaternion.LookRotation((lt - lp).normalized, Vector3.up);
        }
    }

    // a tall phone screen: widen the view so the whole board still fits across
    void FitBoard()
    {
        var cam = Camera.main; if (!cam) return;
        float aspect = (float)Screen.width / Mathf.Max(1, Screen.height);
        cam.fieldOfView = aspect >= 1.2f ? 40f : Mathf.Min(95f, 2f * Mathf.Atan(Mathf.Tan(24f * Mathf.Deg2Rad) / aspect) * Mathf.Rad2Deg);
    }

    // ---------------------------------------------------------------- UI (IMGUI: no extra packages)
    // laid out on a virtual screen whose short side is 720 px, then scaled, so buttons stay finger-sized on phones
    float UiScale => Mathf.Max(1f, Mathf.Min(Screen.width, Screen.height) / 720f);
    float VW => Screen.width / UiScale;
    float VH => Screen.height / UiScale;
    Rect hud = new Rect(16, 16, 330, 240);
    GUIStyle big, mid, btn;
    Font uiFont;   // Japanese-capable font (WebGL's built-in font has no CJK glyphs), loaded from Resources

    bool OverHud(Vector3 mouse)
    {
        var p = new Vector2(mouse.x, Screen.height - mouse.y) / UiScale;
        return mode == Mode.Menu || hud.Contains(p) || promoChoices != null;
    }

    void Styles()
    {
        if (big != null) return;
        if (uiFont == null) uiFont = Resources.Load<Font>("UiFontJP");   // M PLUS 1p (OFL); covers all UI kanji/kana
        big = new GUIStyle(GUI.skin.label) { fontSize = 34, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
        big.normal.textColor = new Color(1f, 0.86f, 0.55f);
        mid = new GUIStyle(GUI.skin.label) { fontSize = 20, wordWrap = true };
        mid.normal.textColor = Color.white;
        btn = new GUIStyle(GUI.skin.button) { fontSize = 20, fixedHeight = 40 };
        if (uiFont != null) { big.font = uiFont; mid.font = uiFont; btn.font = uiFont; }
    }

    void OnGUI()
    {
        Styles();
        // the built-in skin font lacks Japanese glyphs on WebGL; make every GUI control use the loaded JP font
        if (uiFont != null) GUI.skin.font = uiFont;
        GUI.matrix = Matrix4x4.Scale(new Vector3(UiScale, UiScale, 1));
        if (mode == Mode.Menu)
        {
            // the main box is sized to its content (no trailing blank space); the online section is a
            // separate, tight box right below it, so pressing "オンライン対戦" just reveals an independent panel.
            const float menuH = 356f, panelH = 214f, gap = 10f;
            float totalH = onlinePanel ? menuH + gap + panelH : menuH;
            var r = new Rect(VW / 2f - 220, VH / 2f - totalH / 2f, 440, menuH);
            GUI.Box(r, "");
            GUILayout.BeginArea(new Rect(r.x + 20, r.y + 16, r.width - 40, r.height - 32));
            // explicit heights: with a dynamic CJK font, text measurement can differ between the Layout and
            // Repaint passes (glyph atlas rebuilds), which would shift every control below and make the buttons'
            // hit area miss their drawn position. Pinning heights keeps the layout identical in both passes.
            GUILayout.Label("Living Chess", big, GUILayout.Height(46));
            GUILayout.Space(10);
            GUILayout.Label("CPU の強さ", mid, GUILayout.Height(26));
            level = GUILayout.Toolbar(level, LevelNames, btn, GUILayout.Height(40));
            GUILayout.Space(12);
            if (GUILayout.Button("CPU と対戦（白で指す）", btn)) Begin(Mode.VsCpu, 1);
            if (GUILayout.Button("CPU と対戦（黒で指す）", btn)) Begin(Mode.VsCpu, -1);
            if (GUILayout.Button("2人で対戦", btn)) Begin(Mode.TwoPlayers, 1);
            GUILayout.Space(8);
            if (GUILayout.Button("オンライン対戦", btn)) { onlinePanel = !onlinePanel; netError = ""; }
            GUILayout.EndArea();
            if (onlinePanel) OnlinePanel(new Rect(r.x, r.yMax + gap, r.width, panelH));
            return;
        }
        GUI.Box(hud, "");
        GUILayout.BeginArea(new Rect(hud.x + 12, hud.y + 10, hud.width - 24, hud.height - 20));
        GUILayout.Label(StatusText(), mid);
        GUILayout.FlexibleSpace();
        // choose what happens to the camera while a move plays out
        if (GUILayout.Button(watchAngle ? "動くとき: 斜めから見る" : "動くとき: 真上のまま", btn)) watchAngle = !watchAngle;
        GUILayout.BeginHorizontal();
        if (mode == Mode.Online)
        {
            if (netJoined && result == ChessRules.Result.Playing && string.IsNullOrEmpty(netResult) && GUILayout.Button("投了", btn)) StartCoroutine(SendResign());
        }
        else if (GUILayout.Button("最初から", btn)) { NewGame(); yawOffset = 0; }
        if (GUILayout.Button("メニュー", btn)) { NewGame(); mode = Mode.Menu; netGame = null; }
        GUILayout.EndHorizontal();
        GUILayout.EndArea();

        if (promoChoices != null)
        {
            var r = new Rect(VW / 2f - 230, VH - 140, 460, 110);
            GUI.Box(r, "");
            GUILayout.BeginArea(new Rect(r.x + 12, r.y + 10, r.width - 24, r.height - 20));
            GUILayout.Label("昇格する駒を選んでください", mid, GUILayout.Height(26));
            GUILayout.BeginHorizontal();
            foreach (var (name, t) in new[] { ("クイーン", ChessRules.Queen), ("ルーク", ChessRules.Rook), ("ビショップ", ChessRules.Bishop), ("ナイト", ChessRules.Knight) })
                if (GUILayout.Button(name, btn)) { var m = promoChoices.Find(x => Mathf.Abs(x.promo) == t); Commit(m); }
            GUILayout.EndHorizontal();
            GUILayout.EndArea();
        }
        if ((result != ChessRules.Result.Playing || !string.IsNullOrEmpty(netResult)) && !busy)
            GUI.Label(new Rect(0, VH * 0.12f, VW, 60), ResultText(), big);
    }

    void Begin(Mode m, int side)
    {
        NewGame();
        mode = m; humanSide = side; yawOffset = 0;
        yaw = side == 1 ? 0 : 180;
    }

    string StatusText()
    {
        string who = rules.side == 1 ? "白" : "黒";
        string vs = mode == Mode.VsCpu ? $"CPU（{LevelNames[level]}）と対戦 / あなたは{(humanSide == 1 ? "白" : "黒")}"
                  : mode == Mode.Online ? $"オンライン対戦 / あなたは{(humanSide == 1 ? "白" : "黒")}" : "2人で対戦";
        if (mode == Mode.Online && !string.IsNullOrEmpty(netError)) vs += "\n" + netError;
        if (mode == Mode.Online && !netJoined) return vs + $"\nルームコード: {netCode}\n相手の参加を待っています…";
        if (result != ChessRules.Result.Playing || !string.IsNullOrEmpty(netResult)) return vs + "\n" + ResultText();
        string s = vs + $"\n{rules.fullmove}手目　{who}の番";
        if (CpuTurn) s += "（CPU が考え中…）";
        if (mode == Mode.Online && rules.side != humanSide) s += "（相手の番）";
        if (rules.InCheck(rules.side)) s += "\nチェック！";
        return s;
    }

    // ---------------------------------------------------------------- online (room codes; supabase/functions/game)
    OnlineClient net;
    bool onlinePanel, netJoined, netSending, netFetching;
    string netGame, netCode = "", netError = "", netResult = "", codeInput = "";
    int netVersion, netApplied;
    float nextPoll;

    static string NetErrorText(string e)
    {
        switch (e)
        {
            case "no_room": return "その部屋は見つからないか、もう始まっています";
            case "too_many_rooms": return "部屋を作りすぎです。しばらく待ってください";
            case "slow_down": return "操作が速すぎます。少し待ってください";
            case "illegal": return "その手は指せません";
            case "not_your_turn": case "stale": return "盤面を最新にしました";
            case "network": return "通信できませんでした";
            case "auth": return "ログインできませんでした";
            default: return "エラー（" + e + "）";
        }
    }

    void OnlinePanel(Rect r)
    {
        GUI.Box(r, "");
        GUILayout.BeginArea(new Rect(r.x + 20, r.y + 12, r.width - 40, r.height - 24));
        if (net == null) net = new OnlineClient();
        if (!net.Ready) { GUILayout.Label("オンライン対戦の接続先が設定されていません", mid, GUILayout.Height(52)); GUILayout.EndArea(); return; }
        GUILayout.Label("部屋を作る（色を選ぶ）", mid, GUILayout.Height(26));
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("白", btn)) StartCoroutine(CreateRoom("white"));
        if (GUILayout.Button("黒", btn)) StartCoroutine(CreateRoom("black"));
        if (GUILayout.Button("おまかせ", btn)) StartCoroutine(CreateRoom("random"));
        GUILayout.EndHorizontal();
        GUILayout.Label("ルームコードで参加", mid, GUILayout.Height(26));
        GUILayout.BeginHorizontal();
        var field = new GUIStyle(GUI.skin.textField) { fontSize = 22, fixedHeight = 40, font = uiFont };
        codeInput = GUILayout.TextField(codeInput, 6, field, GUILayout.Width(170)).ToUpperInvariant();
        if (GUILayout.Button("参加", btn)) StartCoroutine(JoinRoom(codeInput.Trim()));
        GUILayout.EndHorizontal();
        if (!string.IsNullOrEmpty(netError)) GUILayout.Label(netError, mid, GUILayout.Height(26));
        GUILayout.EndArea();
    }

    IEnumerator CreateRoom(string color)
    {
        netError = "通信中…";
        OnlineClient.GameView v = null;
        yield return net.Create(color, x => v = x);
        if (!string.IsNullOrEmpty(v.error)) { netError = NetErrorText(v.error); yield break; }
        StartOnline(v);
    }

    IEnumerator JoinRoom(string code)
    {
        if (code.Length != 6) { netError = "6文字のコードを入れてください"; yield break; }
        netError = "通信中…";
        OnlineClient.GameView v = null;
        yield return net.Join(code, x => v = x);
        if (!string.IsNullOrEmpty(v.error)) { netError = NetErrorText(v.error); yield break; }
        StartOnline(v);
    }

    void StartOnline(OnlineClient.GameView v)
    {
        Begin(Mode.Online, v.you == "white" ? 1 : -1);
        onlinePanel = false; netError = ""; netResult = "";
        netGame = v.id; netCode = v.code; netVersion = v.version; netApplied = 0; netJoined = v.opponent_joined;
        nextPoll = 0;
    }

    // this player's move goes to the server first; the board plays it only once the server has accepted it
    void Commit(Move m)
    {
        if (mode != Mode.Online) { StartCoroutine(PlayMove(m)); return; }
        StartCoroutine(SendMove(m));
    }

    IEnumerator SendMove(Move m)
    {
        netSending = true; promoChoices = null; selected = -1; selMoves.Clear(); RefreshMarks();
        OnlineClient.GameView v = null;
        yield return net.Move(netGame, m.ToString(), netVersion, x => v = x);
        if (!string.IsNullOrEmpty(v.error))
        {
            netError = NetErrorText(v.error);
            netSending = false; nextPoll = 0;   // re-read the game from the server
            yield break;
        }
        netError = ""; netVersion = v.version; netApplied++;
        netSending = false;
        yield return PlayMove(m);
        ApplyServerStatus(v);
    }

    IEnumerator SendResign()
    {
        netSending = true;
        OnlineClient.GameView v = null;
        yield return net.Resign(netGame, x => v = x);
        netSending = false;
        if (!string.IsNullOrEmpty(v.error)) { netError = NetErrorText(v.error); yield break; }
        netVersion = v.version; ApplyServerStatus(v);
    }

    void OnlinePoll()
    {
        if (net == null || string.IsNullOrEmpty(netGame) || busy || netSending || netFetching || Time.time < nextPoll) return;
        nextPoll = Time.time + 1.5f;
        StartCoroutine(Poll());
    }

    IEnumerator Poll()
    {
        netFetching = true;
        OnlineClient.GameView v = null;
        yield return net.Fetch(netGame, x => v = x);
        netFetching = false;
        if (!string.IsNullOrEmpty(v.error)) { netError = NetErrorText(v.error); yield break; }
        if (netError == NetErrorText("network")) netError = "";
        netJoined = v.opponent_joined;
        if (busy || netSending) yield break;
        if (v.moves.Length > netApplied)
        {
            var m = rules.Legal().Find(x => x.ToString() == v.moves[netApplied]);
            if (m.from == m.to) { Resync(v); yield break; }   // not playable here: rebuild from the server's list
            netApplied++;
            if (netApplied == v.moves.Length) netVersion = v.version;
            nextPoll = 0;   // pick up the next one straight away if there is one
            yield return PlayMove(m);
            if (netApplied == v.moves.Length) ApplyServerStatus(v);
            yield break;
        }
        if (v.moves.Length < netApplied) { Resync(v); yield break; }
        netVersion = v.version;
        ApplyServerStatus(v);
    }

    // the board disagrees with the server: lay the server's game out again without animation
    void Resync(OnlineClient.GameView v)
    {
        NewGame();
        foreach (var t in v.moves)
        {
            var m = rules.Legal().Find(x => x.ToString() == t);
            if (m.from == m.to) break;
            rules.Make(m);
        }
        foreach (var p in live) if (p) Destroy(p.gameObject);
        live.Clear(); System.Array.Clear(at, 0, 64);
        if (fx) fx.ClearTrails();
        for (int s = 0; s < 64; s++) if (rules.b[s] != 0) at[s] = Spawn(rules.b[s], s);
        netApplied = v.moves.Length; netVersion = v.version;
        result = rules.Status();
        RefreshMarks();
        ApplyServerStatus(v);
    }

    void ApplyServerStatus(OnlineClient.GameView v)
    {
        if (v.status == "playing" || v.status == "waiting" || result != ChessRules.Result.Playing) return;
        if (v.reason == "resignation")
            netResult = (v.status == "white_won" ? "黒が投了 — 白の勝ち" : "白が投了 — 黒の勝ち");
        else if (v.status == "abandoned") netResult = "この対局は終了しました";
    }

    string ResultText()
    {
        if (!string.IsNullOrEmpty(netResult)) return netResult;
        switch (result)
        {
            case ChessRules.Result.WhiteMates: return "チェックメイト — 白の勝ち";
            case ChessRules.Result.BlackMates: return "チェックメイト — 黒の勝ち";
            case ChessRules.Result.Stalemate: return "ステイルメイト — 引き分け";
            case ChessRules.Result.FiftyMoves: return "50手ルール — 引き分け";
            case ChessRules.Result.Repetition: return "同じ局面が3回 — 引き分け";
            case ChessRules.Result.NoMaterial: return "駒不足 — 引き分け";
        }
        return "";
    }
}
