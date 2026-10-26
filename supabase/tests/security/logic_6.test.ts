// RED TEAM / logic — field fuzzing: unicode/emoji/null bytes, wrong types, extra fields, unknown actions.
// Strict input validation must reject every one of these (non-200). Exit 0 if all blocked; throw on any accept.
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
const v = j.body.version;

const cases: [string, unknown][] = [
  // unicode / emoji / null bytes in string fields
  ["emoji room code", { action: "join", code: "AB😀CD" }],
  ["null byte in room code", { action: "join", code: "AB\u0000CD" }],
  ["null byte in move", { action: "move", game: id, move: "e2e4\u0000", version: v }],
  ["unicode digits in move", { action: "move", game: id, move: "ｅ２ｅ４", version: v }],
  ["emoji in color", { action: "create", color: "whité" }],
  ["rtl/zero-width in code", { action: "join", code: "A​BCDE" }],
  ["null byte in game id", { action: "move", game: id + "\u0000", move: "e2e4", version: v }],

  // wrong types
  ["action is a number", { action: 123 }],
  ["action is null", { action: null }],
  ["action is an array", { action: ["move"] }],
  ["version is a string", { action: "move", game: id, move: "e2e4", version: "1" }],
  ["version is a float", { action: "move", game: id, move: "e2e4", version: 1.5 }],
  ["version is negative", { action: "move", game: id, move: "e2e4", version: -1 }],
  ["version is boolean", { action: "move", game: id, move: "e2e4", version: true }],
  ["game id is a number", { action: "move", game: 123, move: "e2e4", version: v }],
  ["move is an array", { action: "move", game: id, move: ["e2e4"], version: v }],
  ["move is an object", { action: "move", game: id, move: { from: "e2" }, version: v }],
  ["code is a number", { action: "join", code: 123456 }],
  ["color is a number", { action: "create", color: 1 }],

  // extra / unexpected fields (strict allow-list)
  ["extra field on create", { action: "create", color: "white", admin: true }],
  ["extra field on move", { action: "move", game: id, move: "e2e4", version: v, force: 1 }],
  ["extra field on join", { action: "join", code: "ABCDEF", sql: "x" }],
  ["extra field on resign", { action: "resign", game: id, winner: "me" }],

  // unknown / dangerous action values
  ["unknown action delete", { action: "delete", game: id }],
  ["prototype-pollution action", { action: "__proto__" }],
  ["constructor action", { action: "constructor" }],
  ["empty action", { action: "" }],
  ["missing action", { game: id, move: "e2e4", version: v }],
];

for (const [name, body] of cases) {
  const r = await call(w, body);
  check(name, r.status !== 200, { status: r.status, body: r.body });
}

if (bad) throw new Error(`${bad} malformed field(s) were ACCEPTED`);
console.log("logic_6: all blocked");
process.exit(0);
