// RED TEAM / logic — turn order & piece ownership.
// Attacks: move out of turn, move the opponent's pieces, act on a game that is not yet 'playing'.
// Exit 0 if every attack is BLOCKED; throw (exit 1) if any SUCCEEDS.
import { anon, call } from "../flow.test.ts";

let bad = 0;
const check = (name: string, blocked: boolean, got: unknown) => {
  console.log(`${blocked ? "BLOCKED" : "EXPLOIT"}  ${name}  ${JSON.stringify(got)}`);
  if (!blocked) bad++;
};

const w = await anon(), b = await anon();
const c = await call(w, { action: "create", color: "white" });
if (c.status !== 200) throw new Error("setup create failed: " + JSON.stringify(c));

// --- act before the opponent joined (game still 'waiting')
const early = await call(w, { action: "move", game: c.body.id, move: "e2e4", version: c.body.version });
check("move before opponent joins (waiting game)", early.status !== 200, early.body);

const j = await call(b, { action: "join", code: c.body.code });
if (j.status !== 200) throw new Error("setup join failed: " + JSON.stringify(j));
const id = c.body.id;
let v = j.body.version; // == 1, white to move

// white plays a legal move (this must work, otherwise the rest is meaningless)
const first = await call(w, { action: "move", game: id, move: "e2e4", version: v });
if (first.status !== 200) throw new Error("baseline legal move rejected: " + JSON.stringify(first));
v = first.body.version; // == 2, black to move

// --- white moves AGAIN, out of turn
const outOfTurn = await call(w, { action: "move", game: id, move: "d2d4", version: v });
check("white moves twice in a row (out of turn)", outOfTurn.status !== 200, outOfTurn.body);

// --- white tries to move one of its own pieces while it is black's turn
const whiteAgain = await call(w, { action: "move", game: id, move: "g1f3", version: v });
check("white moves own piece out of turn", whiteAgain.status !== 200, whiteAgain.body);

// --- black (on move) tries to move a WHITE piece
const foreignPiece = await call(b, { action: "move", game: id, move: "e4e5", version: v });
check("black moves the opponent's (white) piece", foreignPiece.status !== 200, foreignPiece.body);

// --- black (on move) tries to move a white piece from its home square
const foreignPiece2 = await call(b, { action: "move", game: id, move: "d2d4", version: v });
check("black moves a white home-rank pawn", foreignPiece2.status !== 200, foreignPiece2.body);

// confirm the board never advanced from the single legal move: a stale replay of the first move stays stale
const stillBlack = await call(b, { action: "move", game: id, move: "e7e5", version: v });
check("sanity: legal black reply still works after attacks", stillBlack.status === 200, stillBlack.body);

if (bad) throw new Error(`${bad} turn/ownership attack(s) SUCCEEDED`);
console.log("logic_1: all blocked");
process.exit(0);
