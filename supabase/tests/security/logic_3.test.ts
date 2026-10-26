// RED TEAM / logic — replay, reorder and stale-version attacks (version compare-and-set).
// A move already applied, or one carrying an old/future version, must never change the game again.
// Exit 0 if all blocked; throw if a stale/replayed move mutates the game.
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

const v1 = j.body.version;                 // 1, white to move
const m1 = await call(w, { action: "move", game: id, move: "e2e4", version: v1 });
if (m1.status !== 200) throw new Error("baseline move failed: " + JSON.stringify(m1));
const v2 = m1.body.version;                // 2, black to move
const m2 = await call(b, { action: "move", game: id, move: "e7e5", version: v2 });
if (m2.status !== 200) throw new Error("baseline move 2 failed: " + JSON.stringify(m2));
const v3 = m2.body.version;                // 3, white to move
const movesNow = m2.body.moves.length;     // 2

// --- replay white's first move with the ORIGINAL (now stale) version
const replayOld = await call(w, { action: "move", game: id, move: "e2e4", version: v1 });
check("replay first move with stale version 1", replayOld.status !== 200, replayOld.body);

// --- resend the same first move with the PREVIOUS version (2) — belongs to black's turn, stale for white
const replayPrev = await call(w, { action: "move", game: id, move: "e2e4", version: v2 });
check("replay first move with stale version 2", replayPrev.status !== 200, replayPrev.body);

// --- future version number that the game has not reached
const future = await call(w, { action: "move", game: id, move: "d2d4", version: 999999 });
check("move with a future version (999999)", future.status !== 200, future.body);

// --- reorder: try to re-apply black's move now that it is white's turn, with the current version
const reorder = await call(w, { action: "move", game: id, move: "e7e5", version: v3 });
check("reapply the opponent's last move (reorder)", reorder.status !== 200, reorder.body);

// Prove nothing above mutated the game: a legitimate move with the current version must land exactly one move on.
const legit = await call(w, { action: "move", game: id, move: "g1f3", version: v3 });
if (legit.status !== 200) throw new Error("current-version move unexpectedly rejected: " + JSON.stringify(legit));
check("game advanced by exactly one move (no stale writes slipped in)",
  legit.body.version === v3 + 1 && legit.body.moves.length === movesNow + 1, legit.body);

if (bad) throw new Error(`${bad} stale/replay attack(s) SUCCEEDED`);
console.log("logic_3: all blocked");
process.exit(0);
