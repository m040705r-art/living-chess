// RED TEAM / authz #5 — pull the hidden position via PostgREST embedding / resource embedding
// Attack: the authoritative chess position lives in private.positions.game_id -> games.id. If that FK were
//         exposed, a player (even a legitimate member) could embed it from the games endpoint and read the
//         full board state the server is supposed to keep secret. Try embedding by table name and by FK name,
//         as a member (A) and as an outsider (C).
// EXIT 0 = no embedding returns a "state" field. throw = the position state leaked.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const h = (t: string) => ({ apikey: KEY, Authorization: `Bearer ${t}`, "Content-Type": "application/json" });

const A = await anon(), C = await anon();
const created = await fetch(`${URL_}/functions/v1/game`, { method: "POST", headers: h(A), body: JSON.stringify({ action: "create", color: "white" }) }).then((r) => r.json());
const gid = created.id as string;
if (!gid) throw new Error("setup: create failed " + JSON.stringify(created));

const embeds = [
  `rest/v1/games?select=*,positions(*)&id=eq.${gid}`,
  `rest/v1/games?select=*,private_positions:positions(*)&id=eq.${gid}`,
  `rest/v1/games?select=*,positions(state)&id=eq.${gid}`,
  `rest/v1/games?select=id,state&id=eq.${gid}`,
  `rest/v1/positions?select=*,games(*)`,
];

const leaks: string[] = [];
for (const t of [A, C]) {
  for (const path of embeds) {
    const r = await fetch(`${URL_}/${path}`, { headers: h(t) });
    const text = await r.text();
    // leak = a 2xx whose body actually contains board state (a "state" key with board data)
    if (r.status >= 200 && r.status < 300 && /"state"\s*:/.test(text) && text.includes("board") || /"state"\s*:\s*\{/.test(text)) {
      leaks.push(`${t === A ? "member" : "outsider"} ${path} -> ${text.slice(0, 200)}`);
    }
    console.log(`  [${r.status}] ${t === A ? "member " : "outsider"} ${path.replace("rest/v1/", "")}`);
  }
}

if (leaks.length) throw new Error("EXPLOITED: hidden position state leaked via embedding:\n" + leaks.join("\n"));
console.log("BLOCKED: private.positions cannot be embedded; the stored position never leaves the server");
process.exit(0);
