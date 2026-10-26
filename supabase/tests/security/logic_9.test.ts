// RED TEAM / logic — perft + "server rejects every illegal move the client could send".
// First confirm the rules engine's move tree matches the known perft counts (so legalMoves is trustworthy),
// then, against the LIVE server in the opening position, fire a broad sample of well-formed-but-illegal moves
// and require the server to reject each one. Exit 0 if all blocked; throw if the server accepts any illegal move.
import { initial, legalMoves, make, moveText, type Position } from "../../functions/_shared/chess.ts";
import { anon, call } from "../flow.test.ts";

let bad = 0;
const check = (name: string, ok: boolean, got: unknown) => {
  console.log(`${ok ? "OK     " : "EXPLOIT"}  ${name}  ${JSON.stringify(got)}`);
  if (!ok) bad++;
};

// ---- 1. perft: the engine the server trusts must count the move tree exactly.
function perft(p: Position, d: number): number {
  if (d === 0) return 1;
  let n = 0;
  for (const m of legalMoves(p)) n += perft(make(p, m), d - 1);
  return n;
}
check("perft d1 == 20", perft(initial(), 1) === 20, perft(initial(), 1));
check("perft d2 == 400", perft(initial(), 2) === 400, perft(initial(), 2));
check("perft d3 == 8902", perft(initial(), 3) === 8902, perft(initial(), 3));

// ---- 2. build a sample of illegal (from->to) strings for the opening position.
const start = initial();
const legal = new Set(legalMoves(start).map(moveText));
const sqName = (s: number) => "abcdefgh"[s & 7] + "12345678"[s >> 3];
const illegal: string[] = [];
for (let from = 0; from < 16; from++) {          // every white-occupied square (back rank + pawns)
  let picked = 0;
  for (let to = 0; to < 64 && picked < 5; to++) {
    const mv = sqName(from) + sqName(to);
    if (legal.has(mv)) continue;                  // skip the genuinely legal ones
    illegal.push(mv);                             // includes from==to (null moves)
    picked++;
  }
}
console.log(`sampling ${illegal.length} illegal opening moves against the live server`);

// ---- 3. fire them at a real game (none should commit; version stays put).
const w = await anon(), b = await anon();
const c = await call(w, { action: "create", color: "white" });
const j = await call(b, { action: "join", code: c.body.code });
if (c.status !== 200 || j.status !== 200) throw new Error("setup failed");
const id = c.body.id;
const v = j.body.version;

let accepted = 0;
const bogus: string[] = [];
for (let i = 0; i < illegal.length; i += 20) {   // chunks of 20 (<= 40 concurrent)
  const chunk = illegal.slice(i, i + 20);
  const res = await Promise.all(chunk.map((mv) => call(w, { action: "move", game: id, move: mv, version: v })));
  res.forEach((r, k) => { if (r.status === 200) { accepted++; bogus.push(chunk[k]); } });
}
check(`server rejected all ${illegal.length} illegal opening moves`, accepted === 0, { accepted, examples: bogus.slice(0, 5) });

// the game must be untouched (still at the join version, no moves recorded)
const read = await fetch(`http://127.0.0.1:54321/rest/v1/games?select=version,moves&id=eq.${id}`,
  { headers: { apikey: "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH", Authorization: `Bearer ${w}` } }).then((r) => r.json());
check("game state unchanged after the illegal barrage", read[0]?.version === v && read[0]?.moves.length === 0, read[0]);

if (bad) throw new Error(`${bad} perft/illegal-move check(s) FAILED`);
console.log("logic_9: all blocked");
process.exit(0);
