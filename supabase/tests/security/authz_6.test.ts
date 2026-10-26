// RED TEAM / authz #6 — does the edge function leak whether a game exists to a non-member?
// Attack: C targets (a) A+B's REAL game id and (b) a random non-existent id, with move and resign.
//         If the real game produced a different status/error than the fake one, C could probe which ids
//         exist and whether they are playing. The function must answer identically ("no_game", 404) in
//         both cases so membership/existence never leaks.
// EXIT 0 = responses are indistinguishable. throw = the real game leaked its existence/state.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const h = (t: string) => ({ apikey: KEY, Authorization: `Bearer ${t}`, "Content-Type": "application/json" });
const post = async (t: string, body: unknown) => {
  const r = await fetch(`${URL_}/functions/v1/game`, { method: "POST", headers: h(t), body: JSON.stringify(body) });
  return { status: r.status, body: (await r.text()).slice(0, 200) };
};

const A = await anon(), B = await anon(), C = await anon();
const created = await fetch(`${URL_}/functions/v1/game`, { method: "POST", headers: h(A), body: JSON.stringify({ action: "create", color: "white" }) }).then((r) => r.json());
const real = created.id as string, code = created.code as string;
if (!real) throw new Error("setup: create failed " + JSON.stringify(created));
await post(B, { action: "join", code });   // game is now 'playing' with A (white) and B (black)
const fake = "11111111-1111-1111-1111-111111111111";

const mismatches: string[] = [];
for (const action of ["move", "resign"] as const) {
  const mk = (id: string) => action === "move" ? { action, game: id, move: "e2e4", version: 1 } : { action, game: id };
  const r1 = await post(C, mk(real));
  const r2 = await post(C, mk(fake));
  console.log(`  ${action}: real=[${r1.status}]${r1.body}  fake=[${r2.status}]${r2.body}`);
  if (r1.status !== r2.status || r1.body !== r2.body) {
    mismatches.push(`${action}: real=${r1.status}/${r1.body} vs fake=${r2.status}/${r2.body}`);
  }
}

if (mismatches.length) throw new Error("EXPLOITED: the function leaks game existence/state to a non-member:\n" + mismatches.join("\n"));
console.log("BLOCKED: real and non-existent games are indistinguishable to a non-member (404 no_game)");
process.exit(0);
