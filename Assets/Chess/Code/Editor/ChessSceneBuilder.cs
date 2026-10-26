using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

// Menus: Chess/Build Pawn Battle Scene -> Scenes/PawnBattle.unity   (storyboard row 1: pawn vs pawn)
//        Chess/Build Knight Battle Scene -> Scenes/KnightBattle.unity (storyboard row 2: knight charges a pawn)
// Rebuilds materials, the animator controllers and the scene from scratch each time (safe to re-run
// after re-exporting the pieces from Blender).
public static class ChessSceneBuilder
{
    const string Root = "Assets/Chess";
    static string Fbx(string piece) => $"{Root}/Art/Models/Pieces/{piece}.fbx";
    static string WalkJsonSrc(string piece) => $"WebPreview/models/{piece}_walk.json";   // written by BlenderSource/export.py
    // Imported pieces already face +Z (checked: the Attack thrust reaches +Z); kept as a hook in case that changes
    public const float ModelFacingFix = 0f;
    // the procedural sound effects (SoundSource/sfx.py) stay wired in but silent until the user wants them
    public const bool SoundOn = false;

    [MenuItem("Chess/Build Pawn Battle Scene")]
    public static void Build() => Build("Pawn", PawnBattle.Matchup.PawnVsPawn, "PawnBattle");

    [MenuItem("Chess/Build Knight Battle Scene")]
    public static void BuildKnight() => Build("Knight", PawnBattle.Matchup.KnightVsPawn, "KnightBattle");

    [MenuItem("Chess/Build Bishop Battle Scene")]
    public static void BuildBishop() => Build("Bishop", PawnBattle.Matchup.BishopVsPawn, "BishopBattle");

    [MenuItem("Chess/Build Rook Battle Scene")]
    public static void BuildRook() => Build("Rook", PawnBattle.Matchup.RookVsPawn, "RookBattle");

    [MenuItem("Chess/Build Queen Battle Scene")]
    public static void BuildQueen() => Build("Queen", PawnBattle.Matchup.QueenVsPawn, "QueenBattle");

    // the playable game (user: "プレイできるようにして"): CPU or two players at one screen, full rules
    [MenuItem("Chess/Build Game Scene")]
    public static void BuildGame()
    {
        var mats = NewStage();
        var game = new GameObject("Chess Game").AddComponent<ChessGame>();
        var types = new[] { "Pawn", "Knight", "Bishop", "Rook", "Queen", "King" };
        game.templates = new ChessPiece[12];
        var holder = new GameObject("Piece Templates").transform;
        for (int t = 0; t < 6; t++)
        {
            var ctrl = Controller(types[t]); var walk = WalkCurve(types[t]);
            for (int c = 0; c < 2; c++)
            {
                var p = Piece(types[t], (c == 0 ? "White " : "Black ") + types[t], c == 0 ? mats.whiteStone : mats.blackStone,
                              mats.gold, mats.shadow, mats.glow, ctrl, walk, Vector3.zero, 0);
                p.transform.SetParent(holder);
                p.gameObject.SetActive(false);
                game.templates[c * 6 + t] = p;
            }
        }
        var pivot = new GameObject("Camera Pivot").transform;
        pivot.position = new Vector3(0.5f, 0, 0.5f);
        var cam = new GameObject("Main Camera").AddComponent<Camera>();
        cam.tag = "MainCamera";
        cam.clearFlags = CameraClearFlags.Skybox;
        cam.fieldOfView = 40; cam.nearClipPlane = 0.05f; cam.farClipPlane = 160;
        cam.transform.SetParent(pivot, false);
        cam.transform.localPosition = new Vector3(0, 9.5f, -9.5f);
        cam.transform.LookAt(pivot.position + new Vector3(0, 0, 0.4f));
        cam.gameObject.AddComponent<AudioListener>();
        game.cameraPivot = pivot;

        var fx = new GameObject("Battle Effects").AddComponent<PawnBattle>();
        fx.autoPlay = false; fx.stoneMaterial = mats.whiteStone; fx.soundOn = SoundOn;
        fx.sfxClips = AssetDatabase.FindAssets("t:AudioClip", new[] { $"{Root}/Audio" })
            .Select(g => AssetDatabase.LoadAssetAtPath<AudioClip>(AssetDatabase.GUIDToAssetPath(g))).ToArray();
        game.fx = fx;
        SaveScene("ChessGame");
    }

    [MenuItem("Chess/Build King Battle Scene")]
    public static void BuildKing() => Build("King", PawnBattle.Matchup.KingVsPawn, "KingBattle");

    // materials, a new scene, the board and the colosseum: shared by the battle demos and the playable game
    struct Mats { public Material whiteStone, blackStone, shadow, gold, glow; }
    static Mats NewStage()
    {
        foreach (var d in new[] { "Materials", "Animation", "Scenes", "Data" })
            if (!AssetDatabase.IsValidFolder($"{Root}/{d}")) AssetDatabase.CreateFolder(Root, d);

        // ---- materials (Chess/Stone)
        var whiteStone = StoneMat("Stone_White", new Color32(0xc9, 0xc6, 0xbf, 255), 0.5f);
        var blackStone = StoneMat("Stone_Black", new Color32(0x2c, 0x2c, 0x31, 255), 0.62f);
        var boardLight = StoneMat("Board_Light", new Color32(0xbf, 0xb8, 0xa8, 255), 0.78f, world: true);
        var boardDark = StoneMat("Board_Dark", new Color32(0x1d, 0x1b, 0x1a, 255), 0.82f, world: true);
        var shadow = PlainMat("Shadow", new Color(0.04f, 0.04f, 0.05f), 0.3f);
        var gold = PlainMat("Gold", new Color32(0xd4, 0xa8, 0x5c, 255), 0.72f);
        gold.SetFloat("_Metallic", 1f);
        var glow = PlainMat("Glow", new Color(0.75f, 0.88f, 1f), 0.8f);   // the bishop's orb
        glow.EnableKeyword("_EMISSION"); glow.SetColor("_EmissionColor", new Color(0.4f, 0.65f, 1f) * 1.5f);
        var rim = PlainMat("BoardRim", new Color32(0x2a, 0x1c, 0x12, 255), 0.4f);
        var flameMat = PlainMat("BrazierFlame", new Color(1f, 0.75f, 0.4f), 0f);
        flameMat.EnableKeyword("_EMISSION"); flameMat.SetColor("_EmissionColor", new Color(1f, 0.55f, 0.2f) * 3.5f);

        // ---- scene
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // board: 8x8 squares centred on integer coordinates, x/z in -3..4
        var board = new GameObject("Board").transform;
        for (int i = 0; i < 8; i++)
            for (int j = 0; j < 8; j++)
            {
                var sq = GameObject.CreatePrimitive(PrimitiveType.Cube);
                Object.DestroyImmediate(sq.GetComponent<Collider>());
                sq.name = $"Square_{(char)('a' + i)}{j + 1}";
                sq.transform.SetParent(board);
                sq.transform.localPosition = new Vector3(i - 3, -0.05f, j - 3);
                sq.transform.localScale = new Vector3(1, 0.1f, 1);
                sq.GetComponent<Renderer>().sharedMaterial = (i + j) % 2 == 0 ? boardDark : boardLight;
            }
        var frame = GameObject.CreatePrimitive(PrimitiveType.Cube);
        Object.DestroyImmediate(frame.GetComponent<Collider>());
        frame.name = "Rim"; frame.transform.SetParent(board);
        frame.transform.localPosition = new Vector3(0.5f, -0.09f, 0.5f); frame.transform.localScale = new Vector3(8.6f, 0.16f, 8.6f);
        frame.GetComponent<Renderer>().sharedMaterial = rim;

        Arena(new Vector3(0.5f, 0, 0.5f));   // the colosseum (user's arena sheet); Stage(...) is the earlier moonlit ruin

        return new Mats { whiteStone = whiteStone, blackStone = blackStone, shadow = shadow, gold = gold, glow = glow };
    }

    static void Build(string whitePiece, PawnBattle.Matchup matchup, string sceneName)
    {
        var mats = NewStage();
        var whiteStone = mats.whiteStone; var blackStone = mats.blackStone; var shadow = mats.shadow; var gold = mats.gold; var glow = mats.glow;
        var setups = new[] { whitePiece, "Pawn" }.Distinct().ToDictionary(n => n, n => (ctrl: Controller(n), walk: WalkCurve(n)));

        // pieces
        var white = Piece(whitePiece, "White " + whitePiece, whiteStone, gold, shadow, glow, setups[whitePiece].ctrl, setups[whitePiece].walk, new Vector3(0, 0, 2), 180f);
        var black = Piece("Pawn", "Black Pawn", blackStone, gold, shadow, glow, setups["Pawn"].ctrl, setups["Pawn"].walk, new Vector3(0, 0, -1), 0f);

        // camera on a slowly orbiting pivot
        var pivot = new GameObject("Camera Pivot").transform;
        pivot.position = new Vector3(0, 0.6f, 0.2f);
        var cam = new GameObject("Main Camera").AddComponent<Camera>();
        cam.tag = "MainCamera";
        cam.clearFlags = CameraClearFlags.Skybox;
        cam.fieldOfView = 40; cam.nearClipPlane = 0.05f; cam.farClipPlane = 160;
        cam.transform.SetParent(pivot);
        cam.transform.localPosition = new Vector3(3.4f, 1.6f, 1.8f);
        cam.transform.LookAt(pivot.position);
        cam.gameObject.AddComponent<AudioListener>();

        var demo = new GameObject("Battle").AddComponent<PawnBattle>();
        demo.white = white; demo.black = black; demo.stoneMaterial = whiteStone; demo.cameraPivot = pivot;
        demo.matchup = matchup;
        demo.soundOn = SoundOn;
        demo.sfxClips = AssetDatabase.FindAssets("t:AudioClip", new[] { $"{Root}/Audio" })
            .Select(g => AssetDatabase.LoadAssetAtPath<AudioClip>(AssetDatabase.GUIDToAssetPath(g))).ToArray();

        SaveScene(sceneName);
    }

    static void SaveScene(string sceneName)
    {
        string scenePath = $"{Root}/Scenes/{sceneName}.unity";
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene(), scenePath);
        var scenes = EditorBuildSettings.scenes.Where(s => s.path != scenePath).ToList();
        scenes.Insert(0, new EditorBuildSettingsScene(scenePath, true));
        EditorBuildSettings.scenes = scenes.ToArray();
        AssetDatabase.SaveAssets();
        Debug.Log("Chess: built " + scenePath);
    }

    // walk speed curve as a TextAsset
    static TextAsset WalkCurve(string piece)
    {
        string dst = $"{Root}/Data/{piece}_walk.json";
        File.Copy(WalkJsonSrc(piece), dst, true);
        AssetDatabase.ImportAsset(dst);
        return AssetDatabase.LoadAssetAtPath<TextAsset>(dst);
    }

    // animator controller: one state per clip, named after it (ChessPiece.Play cross-fades by name)
    static AnimatorController Controller(string piece)
    {
        string path = $"{Root}/Animation/{piece}.controller";
        AssetDatabase.DeleteAsset(path);
        var ctrl = AnimatorController.CreateAnimatorControllerAtPath(path);
        var sm = ctrl.layers[0].stateMachine;
        foreach (var clip in AssetDatabase.LoadAllAssetsAtPath(Fbx(piece)).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")))
        {
            var st = sm.AddState(clip.name);
            st.motion = clip;
            if (clip.name == "Idle") sm.defaultState = st;
        }
        return ctrl;
    }

    static ChessPiece Piece(string piece, string name, Material stone, Material gold, Material shadow, Material glow, AnimatorController ctrl, TextAsset walk, Vector3 pos, float yaw)
    {
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx(piece));
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        go.name = name;
        go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0, yaw + ModelFacingFix, 0));
        foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>())
        {
            r.shadowCastingMode = ShadowCastingMode.On;
            r.updateWhenOffscreen = true;   // falls / lunges leave the bind-pose bounds
            var mats = new Material[r.sharedMesh.subMeshCount];
            for (int i = 0; i < mats.Length; i++) mats[i] = stone;
            if (mats.Length > 1) mats[1] = gold;     // Blender slot order: PieceBody, Trim (gilded), Shadow
            if (mats.Length > 2) mats[2] = shadow;
            if (mats.Length > 3) mats[3] = glow;
            r.sharedMaterials = mats;
        }
        var anim = go.GetComponent<Animator>();   // no ?? : Unity's fake-null missing component is not C# null
        if (anim == null) anim = go.AddComponent<Animator>();
        anim.runtimeAnimatorController = ctrl;
        anim.applyRootMotion = false;
        anim.cullingMode = AnimatorCullingMode.AlwaysAnimate;
        var cp = go.AddComponent<ChessPiece>();
        cp.animator = anim; cp.walkCurve = walk;
        return cp;
    }

    // ---- the stage: the ruin mesh (BlenderSource/stage.py), the night sky, ground mist and the braziers' fire
    static readonly Vector3 MoonDir = new Vector3(-0.82f, 0.45f, 0.36f).normalized;
    static readonly Color SkyHorizon = new Color(0.06f, 0.075f, 0.12f);
    // the four braziers stand off the dais corners (stage.py BRAZIERS), coals at stage height GROUND + 1.16
    static readonly Vector2[] Braziers = { new Vector2(-6.1f, -6.1f), new Vector2(6.1f, -6.1f), new Vector2(-6.1f, 6.1f), new Vector2(6.1f, 6.1f) };

    static void Stage(Vector3 centre, Material flameMat)
    {
        // a moonlit ruin (user: 月夜の廃墟・遺跡): cold moonlight as the key, warm braziers around the dais
        RenderSettings.ambientMode = AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.24f, 0.27f, 0.36f);
        RenderSettings.ambientEquatorColor = new Color(0.12f, 0.12f, 0.15f);
        RenderSettings.ambientGroundColor = new Color(0.02f, 0.02f, 0.03f);
        RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Linear;
        RenderSettings.fogColor = SkyHorizon; RenderSettings.fogStartDistance = 9; RenderSettings.fogEndDistance = 24;
        RenderSettings.skybox = SkyMat();

        var moon = new GameObject("Moon Light").AddComponent<Light>();
        moon.type = LightType.Directional; moon.color = new Color(0.66f, 0.75f, 1f); moon.intensity = 1.0f;
        moon.shadows = LightShadows.Soft; moon.shadowResolution = LightShadowResolution.Medium; moon.shadowNormalBias = 0.3f;
        moon.transform.rotation = Quaternion.LookRotation(-MoonDir);
        var mats = new System.Collections.Generic.Dictionary<string, Material>
        {
            ["Ruin"] = StoneMat("Ruin", new Color(0.47f, 0.48f, 0.51f), 0.22f, world: true),
            ["RuinFloor"] = StoneMat("RuinFloor", new Color(0.34f, 0.35f, 0.37f), 0.2f, world: true),
            ["Earth"] = PlainMat("Earth", new Color(0.05f, 0.055f, 0.05f), 0.05f),
            ["Moss"] = PlainMat("Moss", new Color(0.13f, 0.19f, 0.11f), 0.1f),
        };
        var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Art/Models/Stage.fbx"));
        go.name = "Stage"; go.transform.position = centre; go.isStatic = true;
        foreach (var r in go.GetComponentsInChildren<MeshRenderer>())
        {
            r.sharedMaterials = r.sharedMaterials.Select(m => m != null && mats.TryGetValue(m.name, out var x) ? x : m).ToArray();
            r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true;
            r.gameObject.isStatic = true;
        }

        var mist = LoadOrCreate("Mist", Shader.Find("Chess/Mist"));
        mist.SetTexture("_MainTex", MistNoise()); mist.SetColor("_Color", new Color(0.55f, 0.63f, 0.78f, 0.6f));
        EditorUtility.SetDirty(mist);
        for (int k = 0; k < 2; k++)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Object.DestroyImmediate(q.GetComponent<Collider>());
            q.name = "Mist " + k; q.transform.position = centre + Vector3.up * (k == 0 ? -0.4f : -0.22f);
            q.transform.rotation = Quaternion.Euler(90, k * 40, 0); q.transform.localScale = Vector3.one * 40;
            var r = q.GetComponent<Renderer>();
            r.sharedMaterial = mist; r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
        }

        foreach (var b in Braziers)
        {
            var at = centre + new Vector3(b.x, -0.5f + 1.16f, b.y);
            var fire = new GameObject("Brazier Fire").AddComponent<Brazier>();
            fire.transform.position = at;
            var flames = new Transform[3];
            for (int i = 0; i < 3; i++)
            {
                var f = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                Object.DestroyImmediate(f.GetComponent<Collider>());
                f.name = "Flame"; f.transform.SetParent(fire.transform, false);
                float a = i * 2.1f;
                f.transform.localPosition = new Vector3(Mathf.Cos(a) * 0.1f, 0.12f + i * 0.03f, Mathf.Sin(a) * 0.1f);
                f.transform.localScale = new Vector3(0.13f, 0.5f - i * 0.08f, 0.13f);
                var r = f.GetComponent<Renderer>(); r.sharedMaterial = flameMat; r.shadowCastingMode = ShadowCastingMode.Off;
                flames[i] = f.transform;
            }
            var l = new GameObject("Fire Light").AddComponent<Light>();
            l.transform.SetParent(fire.transform, false); l.transform.localPosition = Vector3.up * 0.5f;
            l.type = LightType.Point; l.color = new Color(1f, 0.58f, 0.24f); l.range = 10; l.intensity = 2.2f;
            fire.fireLight = l; fire.flames = flames;
        }
    }

    // ---- the colosseum (BlenderSource/arena.py): a low golden sun, warm haze, fire bowls round the parapet
    static readonly Vector3 SunDir = new Vector3(0.55f, 0.24f, -0.8f).normalized;
    static readonly Color Haze = new Color(0.86f, 0.68f, 0.5f);

    static void Arena(Vector3 centre)
    {
        RenderSettings.ambientMode = AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.52f, 0.56f, 0.68f);
        RenderSettings.ambientEquatorColor = new Color(0.62f, 0.5f, 0.38f);
        RenderSettings.ambientGroundColor = new Color(0.26f, 0.19f, 0.13f);
        RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Linear;
        RenderSettings.fogColor = Haze; RenderSettings.fogStartDistance = 30; RenderSettings.fogEndDistance = 130;
        var sky = LoadOrCreate("SunsetSky", Shader.Find("Chess/SunsetSky"));
        sky.SetVector("_SunDir", SunDir); EditorUtility.SetDirty(sky);
        RenderSettings.skybox = sky;
        QualitySettings.shadowDistance = 35;   // crisp shadows on the board; the far stands do without

        var sun = new GameObject("Sun Light").AddComponent<Light>();
        sun.type = LightType.Directional; sun.color = new Color(1f, 0.8f, 0.56f); sun.intensity = 1.45f;
        sun.shadows = LightShadows.Soft; sun.shadowResolution = LightShadowResolution.Medium; sun.shadowNormalBias = 0.3f;
        sun.transform.rotation = Quaternion.LookRotation(-SunDir);

        Material M(string name, float gloss, float metal = 0, float noise = 0, float sway = 0, float bob = 0, float flicker = 0, float emission = 0)
        {
            var m = LoadOrCreate(name, Shader.Find("Chess/Arena"));
            m.SetFloat("_Glossiness", gloss); m.SetFloat("_Metallic", metal); m.SetFloat("_NoiseStrength", noise);
            m.SetFloat("_Sway", sway); m.SetFloat("_Bob", bob); m.SetFloat("_Flicker", flicker); m.SetFloat("_Emission", emission);
            EditorUtility.SetDirty(m);
            return m;
        }
        var mats = new System.Collections.Generic.Dictionary<string, Material>
        {
            ["ArenaMarble"] = M("ArenaMarble", 0.45f, noise: 1),
            ["ArenaGold"] = M("ArenaGold", 0.7f, metal: 1),
            ["ArenaCloth"] = M("ArenaCloth", 0.1f, sway: 1),
            ["ArenaCrowd"] = M("ArenaCrowd", 0.1f, bob: 1),
            ["ArenaFire"] = M("ArenaFire", 0f, flicker: 1, emission: 3),
            ["ArenaDark"] = M("ArenaDark", 0.05f),
        };
        var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Art/Models/Arena.fbx"));
        go.name = "Arena"; go.transform.position = centre;
        foreach (var r in go.GetComponentsInChildren<MeshRenderer>())
        {
            r.sharedMaterials = r.sharedMaterials.Select(m => m != null && mats.TryGetValue(m.name, out var x) ? x : m).ToArray();
            // receives the sun's shadows but casts none: drawing the 64k-tri arena into the shadow map took the
            // iGPU (Iris Xe) from ~60 to ~35 fps at 1080p
            r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = true;
        }

        // four of the parapet's fire bowls also light the arena (arena.py: tall pedestals every 36 deg, r 10.25);
        // the other flames are emissive only (iGPU: few pixel lights)
        foreach (float deg in new[] { 36f, 144f, 216f, 324f })
        {
            float a = deg * Mathf.Deg2Rad;
            var fire = new GameObject("Fire Light").AddComponent<Brazier>();
            fire.transform.position = centre + new Vector3(Mathf.Cos(a) * 10.0f, 1.9f, Mathf.Sin(a) * 10.0f);
            var l = fire.gameObject.AddComponent<Light>();
            l.type = LightType.Point; l.color = new Color(1f, 0.6f, 0.28f); l.range = 9; l.intensity = 1.6f;
            l.renderMode = LightRenderMode.ForceVertex;   // per-pixel point lights re-drew the whole arena once per light
            fire.fireLight = l; fire.flames = new Transform[0];
            var crackle = fire.gameObject.AddComponent<AudioSource>();   // SoundSource/sfx.py fire_loop
            crackle.clip = AssetDatabase.LoadAssetAtPath<AudioClip>($"{Root}/Audio/fire_loop.wav");
            crackle.enabled = SoundOn;
            crackle.loop = true; crackle.playOnAwake = true; crackle.spatialBlend = 1; crackle.volume = 0.5f;
            crackle.minDistance = 2; crackle.maxDistance = 14; crackle.rolloffMode = AudioRolloffMode.Linear;
        }
    }

    static Material SkyMat()
    {
        var m = LoadOrCreate("NightSky", Shader.Find("Chess/NightSky"));
        m.SetVector("_MoonDir", MoonDir); m.SetColor("_Horizon", SkyHorizon);
        EditorUtility.SetDirty(m);
        return m;
    }

    // a small tiling value-noise texture (alpha) for the drifting mist
    static Texture2D MistNoise()
    {
        string path = $"{Root}/Materials/MistNoise.asset";
        var old = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        if (old != null) return old;
        const int N = 128;
        var tex = new Texture2D(N, N, TextureFormat.Alpha8, true) { wrapMode = TextureWrapMode.Repeat };
        var px = new Color[N * N];
        var rnd = new System.Random(3);
        float[,] Lattice(int g) { var a = new float[g, g]; for (int i = 0; i < g; i++) for (int j = 0; j < g; j++) a[i, j] = (float)rnd.NextDouble(); return a; }
        var octaves = new[] { Lattice(4), Lattice(8), Lattice(16), Lattice(32) };
        for (int y = 0; y < N; y++)
            for (int x = 0; x < N; x++)
            {
                float v = 0, amp = 0.55f, sum = 0;
                foreach (var lat in octaves)
                {
                    int g = lat.GetLength(0);
                    float fx = x / (float)N * g, fy = y / (float)N * g;
                    int x0 = (int)fx, y0 = (int)fy;
                    float tx = Mathf.SmoothStep(0, 1, fx - x0), ty = Mathf.SmoothStep(0, 1, fy - y0);
                    float a = Mathf.Lerp(lat[x0 % g, y0 % g], lat[(x0 + 1) % g, y0 % g], tx);
                    float c = Mathf.Lerp(lat[x0 % g, (y0 + 1) % g], lat[(x0 + 1) % g, (y0 + 1) % g], tx);
                    v += Mathf.Lerp(a, c, ty) * amp; sum += amp; amp *= 0.5f;
                }
                px[y * N + x] = new Color(1, 1, 1, Mathf.SmoothStep(0.25f, 0.85f, v / sum));
            }
        tex.SetPixels(px); tex.Apply();
        AssetDatabase.CreateAsset(tex, path);
        return tex;
    }

    static Material StoneMat(string name, Color color, float gloss, bool world = false)
    {
        var m = LoadOrCreate(name, Shader.Find("Chess/Stone"));
        m.SetColor("_Color", color); m.SetFloat("_Glossiness", gloss);
        m.SetFloat("_WorldSpace", world ? 1 : 0);
        m.SetFloat("_NoiseScale", world ? 2.2f : 38f); m.SetFloat("_NoiseStrength", world ? 0.9f : 1f);
        EditorUtility.SetDirty(m);
        return m;
    }

    static Material PlainMat(string name, Color color, float gloss)
    {
        var m = LoadOrCreate(name, Shader.Find("Standard"));
        m.color = color; m.SetFloat("_Glossiness", gloss);
        EditorUtility.SetDirty(m);
        return m;
    }

    static Material LoadOrCreate(string name, Shader shader)
    {
        string path = $"{Root}/Materials/{name}.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null) { m = new Material(shader); AssetDatabase.CreateAsset(m, path); }
        m.shader = shader;
        return m;
    }
}
