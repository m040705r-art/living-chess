// RED TEAM / logic — acting on a finished game: move after checkmate, resign twice, move after resignation.
// Once a game leaves 'playing', no further move/resign may be accepted. Exit 0 if all blocked; throw on any accept.
import { anon, call } from "../flow.test.ts";

let bad = 0;
const check = (name: string, blocked: boolean, got: unknown) => {
  console.log(`${blocked ? "BLOCKED" : "EXPLOIT"}  ${name}  ${JSON.stringify(got)}`);
  if (!blocked) bad++;
};

// ---- Game 1: play Scholar's mate to a real checkmate, then try to act on the finished game.
{
  const a = await anon(), b = await anon();
  const c = await call(a, { action: "create", color: "white" });
  const j = await call(b, { action: "join", code: c.body.code });
  if (c.status !== 200 || j.status !== 200) throw new Error("setup failed");
  const id = c.body.id;
  let v = j.body.version;
  const mate: [string, string][] = [[a, "e2e4"], [b, "e7e5"], [a, "f1c4"], [b, "b8c6"], [a, "d1h5"], [b, "g8f6"], [a, "h5f7"]];
  for (const [tok, m] of mate) {
    const r = await call(tok, { action: "move", game: id, move: m, version: v });
    if (r.status !== 200) throw new Error(`mate line broke at ${m}: ${JSON.stringify(r)}`);
    v = r.body.version;
  }
  // confirm the game is actually over (white_won / checkmate) via the player's own read
  const read = await fetch(`http://127.0.0.1:54321/rest/v1/games?select=status,result_reason&id=eq.${id}`,
    { headers: { apikey: "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH", Authorization: `Bearer ${a}` } }).then((r) => r.json());
  check("game ended as white_won by checkmate", read[0]?.status === "white_won" && read[0]?.result_reason === "checkmate", read[0]);

  check("loser moves after checkmate", (await call(b, { action: "move", game: id, move: "a7a6", version: v })).status !== 200, "move-after-mate");
  check("winner moves after checkmate", (await call(a, { action: "move", game: id, move: "e1e2", version: v })).status !== 200, "winner-move-after-mate");
  check("winner resigns a finished game", (await call(a, { action: "resign", game: id })).status !== 200, "resign-after-mate");
  check("loser resigns a finished game", (await call(b, { action: "resign", game: id })).status !== 200, "resign-after-mate-2");
}

// ---- Game 2: resign, then try to resign again and move on the resigned game.
{
  const a = await anon(), b = await anon();
  const c = await call(a, { action: "create", color: "white" });
  const j = await call(b, { action: "join", code: c.body.code });
  if (c.status !== 200 || j.status !== 200) throw new Error("setup failed");
  const id = c.body.id;
  const v = j.body.version;

  const r1 = await call(a, { action: "resign", game: id });
  check("first resignation succeeds (baseline)", r1.status === 200 && r1.body.status === "black_won", r1.body);
  check("same player resigns twice", (await call(a, { action: "resign", game: id })).status !== 200, "resign-twice");
  check("opponent resigns an already-resigned game", (await call(b, { action: "resign", game: id })).status !== 200, "opp-resign");
  check("move on a resigned game", (await call(b, { action: "move", game: id, move: "e7e5", version: v + 1 })).status !== 200, "move-after-resign");
}

if (bad) throw new Error(`${bad} finished-game attack(s) SUCCEEDED`);
console.log("logic_8: all blocked");
process.exit(0);
