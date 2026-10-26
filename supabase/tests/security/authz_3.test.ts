// RED TEAM / authz #3 — call the service-role-only RPCs directly over /rest/v1/rpc
// Attack: the edge function talks to SECURITY DEFINER functions (rate_hit, game_create, game_join,
//         game_commit, game_state, game_housekeeping) with the service role. If any of these is callable
//         by anon/authenticated, an outsider could mint rooms, commit arbitrary positions, read the hidden
//         state, or reset rate limits — bypassing every check in the function. All execute is REVOKEd from
//         anon/authenticated and granted only to service_role.
// EXIT 0 = every RPC refuses (permission denied / not found). throw = any RPC executed for us.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const tok = await anon();
const NIL = "00000000-0000-0000-0000-000000000000";

// correct parameter names, so a success would be a real execution (not an arg mismatch)
const calls: { fn: string; args: Record<string, unknown> }[] = [
  { fn: "rate_hit", args: { p_user: NIL, p_action: "move", p_max: 1, p_window_seconds: 1 } },
  { fn: "game_state", args: { p_game: NIL } },
  { fn: "game_create", args: { p_user: NIL, p_color: "white", p_state: {} } },
  { fn: "game_join", args: { p_user: NIL, p_code: "ABCDEF" } },
  { fn: "game_commit", args: { p_game: NIL, p_version: 0, p_move: "e2e4", p_state: {}, p_status: "playing", p_reason: null } },
  { fn: "game_housekeeping", args: {} },
];

const executed: string[] = [];
for (const token of [tok, undefined]) {   // user token AND bare publishable key (anon role)
  for (const c of calls) {
    const headers: Record<string, string> = { apikey: KEY, "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    const r = await fetch(`${URL_}/rest/v1/rpc/${c.fn}`, { method: "POST", headers, body: JSON.stringify(c.args) });
    const text = await r.text();
    // 2xx means the SECURITY DEFINER function actually ran for an outsider.
    if (r.status >= 200 && r.status < 300) {
      executed.push(`${c.fn} (${token ? "user" : "anon-key"}) -> ${r.status} ${text.slice(0, 160)}`);
    }
    console.log(`  [${r.status}] ${c.fn} (${token ? "user token" : "bare key"})`);
  }
}

if (executed.length) throw new Error("EXPLOITED: service-role RPC executed for an outsider:\n" + executed.join("\n"));
console.log("BLOCKED: none of the privileged RPCs are callable by anon/authenticated");
process.exit(0);
