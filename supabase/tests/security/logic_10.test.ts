// RED TEAM / logic — acting on a game you do not sit in (authorization on the move/resign path).
// A player may only move/resign in a game where they are white or black; everyone else must get "no_game"
// (indistinguishable from "does not exist"). Exit 0 if all blocked; throw if an outsider changes a game.
import { anon, call } from "../flow.test.ts";

let bad = 0;
const check = (name: string, blocked: boolean, got: unknown) => {
  console.log(`${blocked ? "BLOCKED" : "EXPLOIT"}  ${name}  ${JSON.stringify(got)}`);
  if (!blocked) bad++;
};

// Game A between alice (white) and bob (black).
const alice = await anon(), bob = await anon();
const a = await call(alice, { action: "create", color: "white" });
const ja = await call(bob, { action: "join", code: a.body.code });
if (a.status !== 200 || ja.status !== 200) throw new Error("setup A failed");
const idA = a.body.id, vA = ja.body.version;

// Game B between carol (white) and dave (black) — carol is NOT in game A.
const carol = await anon(), dave = await anon();
const bgame = await call(carol, { action: "create", color: "white" });
const jb = await call(dave, { action: "join", code: bgame.body.code });
if (bgame.status !== 200 || jb.status !== 200) throw new Error("setup B failed");
const idB = bgame.body.id;

// --- outsider (carol) tries to move/resign game A
check("outsider moves a game they are not in", (await call(carol, { action: "move", game: idA, move: "e2e4", version: vA })).status !== 200, "carol-move-A");
check("outsider resigns a game they are not in", (await call(carol, { action: "resign", game: idA })).status !== 200, "carol-resign-A");

// --- a brand-new account with no games at all
const mallory = await anon();
check("stranger moves someone else's game", (await call(mallory, { action: "move", game: idA, move: "e2e4", version: vA })).status !== 200, "mallory-move-A");
check("stranger resigns someone else's game", (await call(mallory, { action: "resign", game: idA })).status !== 200, "mallory-resign-A");

// --- a legitimate player of game B points at game A (cross-game confusion)
check("player of B moves in A", (await call(dave, { action: "move", game: idA, move: "e2e4", version: vA })).status !== 200, "dave-move-A");

// --- well-formed but non-existent game id
const fakeId = "00000000-0000-4000-8000-000000000000";
check("move a non-existent game id", (await call(mallory, { action: "move", game: fakeId, move: "e2e4", version: 1 })).status !== 200, "fake-move");
check("resign a non-existent game id", (await call(mallory, { action: "resign", game: fakeId })).status !== 200, "fake-resign");

// --- malformed game id (fails the uuid gate)
check("move with a malformed game id", (await call(mallory, { action: "move", game: "not-a-uuid", move: "e2e4", version: 1 })).status !== 200, "bad-id");

// confirm game A is untouched: alice can still make the opening move at the original version
const legit = await call(alice, { action: "move", game: idA, move: "e2e4", version: vA });
check("game A intact after outsider attacks", legit.status === 200 && legit.body.moves.length === 1, legit.body);

// sanity: game B is a distinct game and also unharmed
check("game B distinct and unharmed", idA !== idB, { idA, idB });

if (bad) throw new Error(`${bad} cross-game/authorization attack(s) SUCCEEDED`);
console.log("logic_10: all blocked");
process.exit(0);
