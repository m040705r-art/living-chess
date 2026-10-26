// RED TEAM / logic — oversized / malformed / deeply-nested request bodies and wrong content type.
// None may be accepted (status 200) and none may crash into a different game state. Blocked = any non-200 that
// is not a 5xx server crash we caused. Exit 0 if all blocked; throw if any body is accepted.
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

// --- body larger than MAX_BODY (512): a valid move padded with a giant string field
const bigMove = JSON.stringify({ action: "move", game: id, move: "e2e4", version: v, pad: "A".repeat(2000) });
const oversized = await call(w, bigMove);
check("oversized body (>512 bytes)", oversized.status !== 200, { status: oversized.status, body: oversized.body });

// --- plain oversized garbage
const garbageBig = await call(w, "x".repeat(5000));
check("oversized non-JSON garbage", garbageBig.status !== 200, { status: garbageBig.status });

// --- malformed JSON
const malformed = await call(w, "{ this is not : json ]");
check("malformed JSON", malformed.status !== 200, { status: malformed.status, body: malformed.body });

// --- valid JSON but not an object
check("top-level array body", (await call(w, "[1,2,3]")).status !== 200, "array");
check("top-level number body", (await call(w, "42")).status !== 200, "number");
check("top-level null body", (await call(w, "null")).status !== 200, "null");
check("top-level string body", (await call(w, "\"hello\"")).status !== 200, "string");

// --- deeply nested JSON (within the size limit) in a field the server will reject by type
const nested = "[".repeat(100) + "0" + "]".repeat(100);
const deep = await call(w, `{"action":"create","color":${nested}}`);
check("deeply nested JSON in a field", deep.status !== 200, { status: deep.status, body: deep.body });

// deeply nested as the whole body
const deepBody = await call(w, "[".repeat(120) + "]".repeat(120));
check("deeply nested array as whole body", deepBody.status !== 200, { status: deepBody.status });

// --- wrong content type (defeat the application/json gate)
const wrongCt = await call(w, JSON.stringify({ action: "move", game: id, move: "e2e4", version: v }), { "Content-Type": "text/plain" });
check("wrong Content-Type", wrongCt.status !== 200, { status: wrongCt.status, body: wrongCt.body });

// --- empty body
check("empty body", (await call(w, "")).status !== 200, "empty");

if (bad) throw new Error(`${bad} malformed-body attack(s) were ACCEPTED`);
console.log("logic_5: all blocked");
process.exit(0);
