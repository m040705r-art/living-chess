// RED TEAM / authz #8 — change a game you do not sit in, through the edge function
// Attack: A (white) and B (black) are in a live game. Outsider C tries to move and to resign IN THAT GAME
//         via the function. The function loads the row with the service role but must reject anyone who is
//         not white or black (returns 404 no_game). A successful move/resign by C, or any change to the
//         game's version/status caused by C, is a broken-access-control exploit.
// EXIT 0 = C cannot touch the game and its version is unchanged. throw = C altered the game.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const h = (t: string) => ({ apikey: KEY, Authorization: `Bearer ${t}`, "Content-Type": "application/json" });
const post = async (t: string, body: unknown) => {
  const r = await fetch(`${URL_}/functions/v1/game`, { method: "POST", headers: h(t), body: JSON.stringify(body) });
  let j: any = null; try { j = JSON.parse(await r.text()); } catch { /* */ }
  return { status: r.status, body: j };
};

const A = await anon(), B = await anon(), C = await anon();
const created = await post(A, { action: "create", color: "white" });
const gid = created.body?.id as string, code = created.body?.code as string;
if (!gid) throw new Error("setup: create failed " + JSON.stringify(created));
const joined = await post(B, { action: "join", code });
const vStart = joined.body?.version as number;
if (joined.body?.you !== "black") throw new Error("setup: join failed " + JSON.stringify(joined));

const leaks: string[] = [];

// C tries to move (white's turn, version matches). Must be 404 no_game.
for (const ver of [vStart, 0, 1]) {
  const r = await post(C, { action: "move", game: gid, move: "e2e4", version: ver });
  console.log(`  C move ver=${ver}: [${r.status}] ${JSON.stringify(r.body)}`);
  if (r.status === 200) leaks.push(`C moved in a game it does not sit in (ver=${ver}): ${JSON.stringify(r.body)}`);
}
// C tries to resign. Must be 404 no_game.
const rs = await post(C, { action: "resign", game: gid });
console.log(`  C resign: [${rs.status}] ${JSON.stringify(rs.body)}`);
if (rs.status === 200) leaks.push(`C resigned a game it does not sit in: ${JSON.stringify(rs.body)}`);

// Confirm the game is untouched: A (member) reads it; version and status unchanged.
const after = await fetch(`${URL_}/rest/v1/games?select=version,status,moves&id=eq.${gid}`, { headers: h(A) }).then((r) => r.json());
const row = Array.isArray(after) ? after[0] : null;
console.log(`  game after attacks: ${JSON.stringify(row)}`);
if (!row) throw new Error("control: member A could not re-read the game");
if (row.version !== vStart) leaks.push(`game version changed by outsider: ${vStart} -> ${row.version}`);
if (row.status !== "playing") leaks.push(`game status changed by outsider: playing -> ${row.status}`);
if (Array.isArray(row.moves) && row.moves.length !== 0) leaks.push(`moves were appended by outsider: ${JSON.stringify(row.moves)}`);

if (leaks.length) throw new Error("EXPLOITED: outsider changed a game it does not sit in:\n" + leaks.join("\n"));
console.log("BLOCKED: outsider cannot move/resign; game version & status unchanged");
process.exit(0);
