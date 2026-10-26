using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

// Talks to the Supabase backend (supabase/): an anonymous session, the `game` Edge Function for every change
// (create / join / move / resign) and a read of the player's own game row (RLS lets nobody else read it).
// Only the project URL and the *publishable* key ship with the client; the server checks everything else.
public class OnlineClient
{
    [Serializable] public class Config { public string url; public string publishableKey; }
    [Serializable] class Session { public string access_token; public string refresh_token; public long expires_at; }
    [Serializable] public class GameView
    {
        public string id, code, status, reason, you, error;
        public string[] moves;
        public int version;
        public bool opponent_joined;
    }
    [Serializable] class GameRow { public string id, code, white, black, status, result_reason; public string[] moves; public int version; }
    [Serializable] class GameRows { public GameRow[] rows; }

    readonly Config cfg;
    Session session;
    const string RefreshKey = "living_chess_refresh";

    public bool Ready => cfg != null && !string.IsNullOrEmpty(cfg.url) && !string.IsNullOrEmpty(cfg.publishableKey);
    public string LastError { get; private set; }

    public OnlineClient()
    {
        var t = Resources.Load<TextAsset>("OnlineConfig");
        if (t) cfg = JsonUtility.FromJson<Config>(t.text);
        if (cfg != null) cfg.url = cfg.url.TrimEnd('/');
        // only https (or the local development stack) - never send a token over plain http to a remote host
        if (cfg != null && !(cfg.url.StartsWith("https://") || cfg.url.StartsWith("http://127.0.0.1") || cfg.url.StartsWith("http://localhost")))
            cfg = null;
    }

    // ---------------------------------------------------------------- session
    public IEnumerator EnsureSession()
    {
        LastError = null;
        long now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        if (session != null && session.expires_at - 60 > now) yield break;
        string refresh = session?.refresh_token ?? PlayerPrefs.GetString(RefreshKey, "");
        if (!string.IsNullOrEmpty(refresh))
        {
            yield return Auth("token?grant_type=refresh_token", "{\"refresh_token\":" + Quote(refresh) + "}");
            if (session != null) yield break;
        }
        yield return Auth("signup", "{}");   // anonymous sign-in
    }

    IEnumerator Auth(string path, string json)
    {
        using var req = Post(cfg.url + "/auth/v1/" + path, json, false);
        yield return req.SendWebRequest();
        if (req.result != UnityWebRequest.Result.Success) { session = null; LastError = "auth"; yield break; }
        var s = JsonUtility.FromJson<Session>(req.downloadHandler.text);
        if (s == null || string.IsNullOrEmpty(s.access_token)) { session = null; LastError = "auth"; yield break; }
        session = s;
        PlayerPrefs.SetString(RefreshKey, s.refresh_token); PlayerPrefs.Save();
    }

    // ---------------------------------------------------------------- the game function
    public IEnumerator Call(string json, Action<GameView> done)
    {
        yield return EnsureSession();
        if (session == null) { done(new GameView { error = LastError ?? "auth" }); yield break; }
        using var req = Post(cfg.url + "/functions/v1/game", json, true);
        yield return req.SendWebRequest();
        GameView v = null;
        try { v = JsonUtility.FromJson<GameView>(req.downloadHandler?.text ?? ""); } catch { }
        if (req.result != UnityWebRequest.Result.Success && (v == null || string.IsNullOrEmpty(v.error)))
            v = new GameView { error = req.responseCode == 0 ? "network" : "http_" + req.responseCode };
        done(v ?? new GameView { error = "bad_reply" });
    }

    public IEnumerator Create(string color, Action<GameView> done) => Call("{\"action\":\"create\",\"color\":" + Quote(color) + "}", done);
    public IEnumerator Join(string code, Action<GameView> done) => Call("{\"action\":\"join\",\"code\":" + Quote(code) + "}", done);
    public IEnumerator Move(string game, string move, int version, Action<GameView> done)
        => Call("{\"action\":\"move\",\"game\":" + Quote(game) + ",\"move\":" + Quote(move) + ",\"version\":" + version + "}", done);
    public IEnumerator Resign(string game, Action<GameView> done) => Call("{\"action\":\"resign\",\"game\":" + Quote(game) + "}", done);

    // the game row as RLS shows it to this player
    public IEnumerator Fetch(string game, Action<GameView> done)
    {
        yield return EnsureSession();
        if (session == null) { done(new GameView { error = "auth" }); yield break; }
        string url = cfg.url + "/rest/v1/games?select=id,code,white,black,moves,status,result_reason,version&id=eq." + UnityWebRequest.EscapeURL(game);
        using var req = UnityWebRequest.Get(url);
        Headers(req, true);
        req.timeout = 10;
        yield return req.SendWebRequest();
        if (req.result != UnityWebRequest.Result.Success) { done(new GameView { error = "network" }); yield break; }
        var rows = JsonUtility.FromJson<GameRows>("{\"rows\":" + req.downloadHandler.text + "}");
        if (rows?.rows == null || rows.rows.Length == 0) { done(new GameView { error = "no_game" }); yield break; }
        var g = rows.rows[0];
        done(new GameView
        {
            id = g.id, code = g.code, status = g.status, reason = g.result_reason, moves = g.moves ?? new string[0], version = g.version,
            opponent_joined = !string.IsNullOrEmpty(g.white) && !string.IsNullOrEmpty(g.black),
        });
    }

    // ---------------------------------------------------------------- plumbing
    UnityWebRequest Post(string url, string json, bool withUser)
    {
        var req = new UnityWebRequest(url, "POST")
        {
            uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json)),
            downloadHandler = new DownloadHandlerBuffer(),
            timeout = 10,
        };
        req.SetRequestHeader("Content-Type", "application/json");
        Headers(req, withUser);
        return req;
    }

    void Headers(UnityWebRequest req, bool withUser)
    {
        req.SetRequestHeader("apikey", cfg.publishableKey);
        if (withUser && session != null) req.SetRequestHeader("Authorization", "Bearer " + session.access_token);
        else if (cfg.publishableKey.StartsWith("eyJ")) req.SetRequestHeader("Authorization", "Bearer " + cfg.publishableKey);   // legacy anon JWT
    }

    static string Quote(string s)
    {
        var sb = new StringBuilder("\"");
        foreach (char c in s ?? "")
        {
            if (c == '"' || c == '\\') sb.Append('\\').Append(c);
            else if (c < 0x20) sb.AppendFormat("\\u{0:x4}", (int)c);
            else sb.Append(c);
        }
        return sb.Append('"').ToString();
    }
}
