// RED TEAM / session surface #4 — room-code enumeration: can an outsider guess a code and join a stranger's game?
// Controls under test: 6 chars from a 32-symbol alphabet (32^6 = 1,073,741,824 codes), join limited to 20/600s per
// user, 30-minute room expiry, and a UNIFORM 404 "no_room" for every failure (no "exists but full / expired" oracle).
// Attack: (a) prove there is no response oracle, (b) actually fire a burst of random guesses and confirm none joins a
// stranger's room. BLOCKED => no guess succeeds and all failures look identical. exit 0.
// EXPLOITED => a random guess joins someone else's game, or the error distinguishes a real code from a fake one. throw.
import { anon, call } from "../flow.test.ts";
const fails: string[] = [];
const ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const rand = () => Array.from({ length: 6 }, () => ALPHA[Math.floor(Math.random() * 32)]).join("");

// --- (a) RESPONSE ORACLE: does "no such code" differ from "code exists but not joinable (full)"?
// Build a real, FULL game (two players, status=playing) and try to join its real code with a third account.
const host = await anon(), guest = await anon(), attacker = await anon();
const created = await call(host, { action: "create", color: "white" });
const realCode: string = created.body.code;
const joined = await call(guest, { action: "join", code: realCode });
if (created.status !== 200 || joined.status !== 200) fails.push("setup: could not build a full game to probe the oracle");

const joinReal = await call(attacker, { action: "join", code: realCode });       // real code, but room is full/playing
const joinFake = await call(attacker, { action: "join", code: rand() });          // code that (almost surely) does not exist
console.log(`join real-but-full : status=${joinReal.status} body=${JSON.stringify(joinReal.body)}`);
console.log(`join nonexistent   : status=${joinFake.status} body=${JSON.stringify(joinFake.body)}`);

// Attacker must NOT have been seated in the stranger's game.
if (joinReal.status === 200 && joinReal.body?.you) fails.push(`ORACLE/ACCESS: attacker joined a full stranger game via its code (you=${joinReal.body.you})`);
// Both failures must be indistinguishable (same status + same error) — otherwise the code is an enumeration oracle.
if (!(joinReal.status === joinFake.status && JSON.stringify(joinReal.body) === JSON.stringify(joinFake.body)))
  fails.push(`ORACLE: real-but-full (${joinReal.status}/${JSON.stringify(joinReal.body)}) != nonexistent (${joinFake.status}/${JSON.stringify(joinFake.body)}) — leaks which codes exist`);

// --- (b) BRUTE FORCE burst: fire random guesses from several fresh accounts and confirm none lands on a live room.
// (Each account is capped at 20 joins/600s; here we stay within budget and just prove guesses don't connect.)
let guesses = 0, hits = 0, throttles = 0;
for (let a = 0; a < 3; a++) {
  const t = await anon();
  const results = await Promise.all(Array.from({ length: 15 }, () => call(t, { action: "join", code: rand() })));
  for (const r of results) {
    guesses++;
    if (r.status === 200 && r.body?.id) hits++;
    else if (r.status === 429) throttles++;
  }
}
console.log(`brute-force burst: ${guesses} random guesses -> ${hits} hits, ${throttles} throttled`);
if (hits > 0) fails.push(`BRUTE-FORCE: ${hits}/${guesses} random codes joined a live room — space too small or codes predictable`);

// Feasibility note (reasoned, not a failure): 32^6 = 1.07e9 codes; per-account join rate = 20/600s = 2/min.
// Even amplified via free account-minting (see session_3), expected guesses to hit ONE specific 30-min room ~5.4e8,
// so a targeted join-hijack is infeasible unless a very large number of rooms are open at once.
console.log("note: code space 1.07e9, 30-min expiry, uniform 404 -> targeted brute force infeasible in practice");

if (fails.length) { console.error(`\n${fails.length} EXPLOITED:\n` + fails.join("\n")); process.exit(1); }
console.log("\nroom-code enumeration BLOCKED (no oracle, no guess connected)");
process.exit(0);
