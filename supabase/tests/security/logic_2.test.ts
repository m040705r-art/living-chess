// RED TEAM / logic — illegal / teleport / blocked moves from the initial position.
// Every string here matches the server's move regex but is NOT a legal chess move, so the server must reject
// each one WITHOUT changing the game. Exit 0 if all blocked; throw if any is accepted (status 200).
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
const v = j.body.version; // white to move, nothing has moved

// from -> to strings that are well-formed but illegal in the opening position
const illegal: [string, string][] = [
  ["e2e5", "pawn jumps three squares"],
  ["e2e6", "pawn teleports across the board"],
  ["a1a4", "rook jumps over its own pawn"],
  ["a1a8", "rook slides the whole file through pieces"],
  ["d1d4", "queen moves through its own pawn"],
  ["d1h5", "queen leaps over pieces to h5"],
  ["c1h6", "bishop passes through the d2 pawn"],
  ["e1e3", "king moves two squares (no castling)"],
  ["e1g1", "king-side castle with pieces in the way"],
  ["b1b3", "knight makes a non-knight move"],
  ["b1d2", "knight lands on its own pawn"],
  ["e2e2", "null move (from == to)"],
  ["e2d3", "pawn steps diagonally with nothing to capture"],
  ["e1e2", "king walks onto its own pawn"],
  ["a2a1", "pawn moves backward"],
  ["h2h5", "edge pawn triple-step"],
  ["e2e4q", "promotion suffix on a non-promoting move"],
  ["e7e5", "move a black pawn while white is to move"],
  ["g8f6", "move a black knight while white is to move"],
];

for (const [mv, why] of illegal) {
  const r = await call(w, { action: "move", game: id, move: mv, version: v });
  check(`illegal ${mv} (${why})`, r.status !== 200, r.body);
}

if (bad) throw new Error(`${bad} illegal move(s) were ACCEPTED`);
console.log("logic_2: all blocked");
process.exit(0);
