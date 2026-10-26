// RED TEAM / logic — promotion edge cases, exercised at a REAL promotion (a white pawn reaches b8 by legal play).
// The server must reject king-promotion, missing/double promotion suffixes and impossible promotions, while
// accepting a valid underpromotion. Exit 0 if the bogus forms are blocked and a legal one works; throw otherwise.
import { anon, call } from "../flow.test.ts";

let bad = 0;
const check = (name: string, blocked: boolean, got: unknown) => {
  console.log(`${blocked ? "BLOCKED" : "EXPLOIT"}  ${name}  ${JSON.stringify(got)}`);
  if (!blocked) bad++;
};

const w = await anon(), b = await anon();
const c = await call(w, { action: "create", color: "white" });
const j = await call(b, { action: "join", code: c.body.code });
if (c.status !== 200 || j.status !== 200) throw new Error("setup failed");
const id = c.body.id;
let v = j.body.version;

// Legal cooperative line that marches a white pawn to c7, poised to promote by capturing the b8 knight.
const line: [string, string][] = [
  [w, "d2d4"], [b, "e7e5"], [w, "d4e5"], [b, "d7d6"], [w, "e5d6"], [b, "g8f6"], [w, "d6c7"], [b, "a7a6"],
];
for (const [tok, m] of line) {
  const r = await call(tok, { action: "move", game: id, move: m, version: v });
  if (r.status !== 200) throw new Error(`setup line broke at ${m}: ${JSON.stringify(r)}`);
  v = r.body.version;
}
// now white to move, a pawn on c7 (version v); c7xb8=promotion is the only promotion available

// bogus promotion strings must all be rejected WITHOUT advancing the game
const bogus: [string, string][] = [
  ["c7b8k", "promote to KING (regex must reject)"],
  ["c7b8K", "uppercase promotion piece"],
  ["c7b8", "promoting move missing its promotion piece"],
  ["c7b8qq", "double promotion suffix"],
  ["c7b8p", "promote to pawn"],
  ["c7c8q", "straight push promotion onto an occupied square"],
  ["c7a8q", "promotion with impossible (non-diagonal) pawn geometry"],
];
for (const [mv, why] of bogus) {
  const r = await call(w, { action: "move", game: id, move: mv, version: v });
  check(`bogus promotion ${mv} (${why})`, r.status !== 200, r.body);
}

// a legal underpromotion (to a knight) MUST still be accepted — confirms we were really at a promotion.
const legit = await call(w, { action: "move", game: id, move: "c7b8n", version: v });
check("legal underpromotion c7b8n is accepted", legit.status === 200 && legit.body.moves.at(-1) === "c7b8n", legit.body);

// from the opening position, promotion strings for pieces that cannot promote must also be rejected
const w2 = await anon(), b2 = await anon();
const c2 = await call(w2, { action: "create", color: "white" });
const j2 = await call(b2, { action: "join", code: c2.body.code });
const id2 = c2.body.id, v2 = j2.body.version;
for (const mv of ["e2e1q", "e7e8q", "a2a1n", "e2e4q"]) {
  const r = await call(w2, { action: "move", game: id2, move: mv, version: v2 });
  check(`opening bogus promotion ${mv}`, r.status !== 200, r.body);
}

if (bad) throw new Error(`${bad} promotion attack(s) SUCCEEDED`);
console.log("logic_7: all blocked");
process.exit(0);
