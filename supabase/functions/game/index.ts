// The one door through which online games change: create a room, join it by code, make a move, resign.
// Every request is authenticated (Supabase JWT), rate limited, strictly validated, and checked against the
// server's own copy of the position. Clients can only read their own games (RLS) and never write tables.
import { initial, isPosition, legalMoves, make, moveText, status, type Position } from "../_shared/chess.ts";

const URL_ = Deno.env.get("SUPABASE_URL")!;
const ANON = Deno.env.get("SUPABASE_ANON_KEY")!;
const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
// only the game's own pages may call this from a browser (comma-separated list, set as a function secret)
const ALLOWED = (Deno.env.get("ALLOWED_ORIGINS") ?? "").split(",").map((s) => s.trim()).filter(Boolean);

// no client library: plain fetch to the REST / auth endpoints (fast cold start, no third-party code in the path)
const SERVICE_HEADERS = { apikey: SERVICE, Authorization: `Bearer ${SERVICE}`, "Content-Type": "application/json" };

async function rpc(fn: string, args: Record<string, unknown>): Promise<{ data: any; error: string | null }> {
  const r = await fetch(`${URL_}/rest/v1/rpc/${fn}`, { method: "POST", headers: SERVICE_HEADERS, body: JSON.stringify(args) });
  const text = await r.text();
  if (!r.ok) return { data: null, error: text.slice(0, 200) };
  return { data: text ? JSON.parse(text) : null, error: null };
}

async function gameRow(id: string): Promise<{ data: any; error: string | null }> {
  const r = await fetch(`${URL_}/rest/v1/games?select=*&id=eq.${id}`, { headers: SERVICE_HEADERS });
  if (!r.ok) return { data: null, error: "select" };
  const rows = await r.json();
  return { data: rows[0] ?? null, error: null };
}

// the token is checked by the auth server itself (signature, expiry, revocation), not just decoded here
async function userId(auth: string): Promise<string | null> {
  const r = await fetch(`${URL_}/auth/v1/user`, { headers: { apikey: ANON, Authorization: auth } });
  if (!r.ok) return null;
  const u = await r.json();
  return typeof u?.id === "string" && RE_UUID.test(u.id) ? u.id : null;
}

const RE_CODE = /^[A-HJ-NP-Z2-9]{6}$/;
const RE_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const RE_MOVE = /^[a-h][1-8][a-h][1-8][nbrq]?$/;
const MAX_BODY = 512;
const LIMITS: Record<string, [number, number]> = {   // action -> [max hits, per seconds]
  create: [5, 600], join: [20, 600], move: [90, 60], resign: [10, 600],
};

function cors(origin: string | null): Record<string, string> {
  const h: Record<string, string> = {
    "Vary": "Origin",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
  };
  if (origin && ALLOWED.includes(origin)) {
    h["Access-Control-Allow-Origin"] = origin;
    h["Access-Control-Allow-Headers"] = "authorization, apikey, content-type";
    h["Access-Control-Allow-Methods"] = "POST, OPTIONS";
    h["Access-Control-Max-Age"] = "600";
  }
  return h;
}

function reply(origin: string | null, code: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status: code, headers: { ...cors(origin), "Content-Type": "application/json" } });
}
const fail = (origin: string | null, code: number, error: string) => reply(origin, code, { error });

// what a player may see of a game (never the stored position or the other player's account details)
function view(g: Record<string, unknown>, me: string) {
  return {
    id: g.id, code: g.code, moves: g.moves, status: g.status, reason: g.result_reason, version: g.version,
    you: g.white === me ? "white" : g.black === me ? "black" : null,
    opponent_joined: g.white !== null && g.black !== null,
  };
}

Deno.serve(async (req) => {
  const origin = req.headers.get("Origin");
  // a browser from anywhere else gets no CORS headers; non-browser callers still need a valid user token below
  if (origin && !ALLOWED.includes(origin)) return fail(null, 403, "origin");
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
  if (req.method !== "POST") return fail(origin, 405, "method");
  if (!(req.headers.get("Content-Type") ?? "").startsWith("application/json")) return fail(origin, 415, "content_type");

  // ---- who is asking (the token is verified by the auth server, not just decoded)
  const auth = req.headers.get("Authorization") ?? "";
  if (!auth.startsWith("Bearer ") || auth.length > 4096) return fail(origin, 401, "auth");
  const me = await userId(auth);
  if (!me) return fail(origin, 401, "auth");

  // ---- strict input
  const raw = await req.text();
  if (raw.length > MAX_BODY) return fail(origin, 413, "too_large");
  let body: Record<string, unknown>;
  try { body = JSON.parse(raw); } catch { return fail(origin, 400, "json"); }
  if (!body || typeof body !== "object" || Array.isArray(body)) return fail(origin, 400, "json");
  const action = body.action;
  if (typeof action !== "string" || !(action in LIMITS)) return fail(origin, 400, "action");
  const allowedKeys: Record<string, string[]> = {
    create: ["action", "color"], join: ["action", "code"], move: ["action", "game", "move", "version"], resign: ["action", "game"],
  };
  if (Object.keys(body).some((k) => !allowedKeys[action].includes(k))) return fail(origin, 400, "fields");

  const [max, per] = LIMITS[action];
  const { data: ok, error: rlErr } = await rpc("rate_hit", { p_user: me, p_action: action, p_max: max, p_window_seconds: per });
  if (rlErr) return fail(origin, 500, "server");
  if (!ok) return fail(origin, 429, "slow_down");

  try {
    if (action === "create") {
      const color = body.color === "random" || body.color === undefined ? (crypto.getRandomValues(new Uint8Array(1))[0] & 1 ? "white" : "black") : body.color;
      if (color !== "white" && color !== "black") return fail(origin, 400, "color");
      await rpc("game_housekeeping");
      const { data: g, error } = await rpc("game_create", { p_user: me, p_color: color, p_state: initial() });
      if (error) return fail(origin, error.includes("too_many_rooms") ? 429 : 500, error.includes("too_many_rooms") ? "too_many_rooms" : "server");
      return reply(origin, 200, view(g, me));
    }

    if (action === "join") {
      const code = typeof body.code === "string" ? body.code.toUpperCase() : "";
      if (!RE_CODE.test(code)) return fail(origin, 400, "code");
      const { data: g, error } = await rpc("game_join", { p_user: me, p_code: code });
      if (error) return fail(origin, 500, "server");
      if (!g || !g.id) return fail(origin, 404, "no_room");   // same answer for "no such code", "full", "expired"
      return reply(origin, 200, view(g, me));
    }

    // move / resign: the game must exist and the caller must sit in it
    const id = body.game;
    if (typeof id !== "string" || !RE_UUID.test(id)) return fail(origin, 400, "game");
    const { data: g, error: gErr } = await gameRow(id);
    if (gErr) return fail(origin, 500, "server");
    if (!g || (g.white !== me && g.black !== me)) return fail(origin, 404, "no_game");   // no hint whether it exists
    if (g.status !== "playing") return fail(origin, 409, "not_playing");
    const mySide = g.white === me ? 1 : -1;

    const { data: stateRaw, error: sErr } = await rpc("game_state", { p_game: id });
    if (sErr || !isPosition(stateRaw)) return fail(origin, 500, "server");
    const pos = stateRaw as Position;

    if (action === "resign") {
      const { data: done, error } = await rpc("game_commit", {
        p_game: id, p_version: g.version, p_move: null, p_state: pos,
        p_status: mySide === 1 ? "black_won" : "white_won", p_reason: "resignation",
      });
      if (error) return fail(origin, 500, "server");
      if (!done || !done.id) return fail(origin, 409, "stale");
      return reply(origin, 200, view(done, me));
    }

    // move
    const mv = body.move, ver = body.version;
    if (typeof mv !== "string" || !RE_MOVE.test(mv)) return fail(origin, 400, "move");
    if (!Number.isInteger(ver) || (ver as number) < 0) return fail(origin, 400, "version");
    if (ver !== g.version) return fail(origin, 409, "stale");
    if (pos.side !== mySide) return fail(origin, 409, "not_your_turn");
    const legal = legalMoves(pos).find((m) => moveText(m) === mv);
    if (!legal) return fail(origin, 422, "illegal");
    const next = make(pos, legal);
    const st = status(next);
    const { data: done, error } = await rpc("game_commit", {
      p_game: id, p_version: g.version, p_move: mv, p_state: next,
      p_status: st.result, p_reason: st.reason || null,
    });
    if (error) return fail(origin, 500, "server");
    if (!done || !done.id) return fail(origin, 409, "stale");
    return reply(origin, 200, view(done, me));
  } catch {
    return fail(origin, 500, "server");   // never echo internals
  }
});
