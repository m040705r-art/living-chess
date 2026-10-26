// RED TEAM / session surface #1 — JWT forgery & identity spoofing against the game edge function.
// Attacks: no token, publishable key as bearer, garbage token, tampered signature, tampered payload (sub),
//          alg=none forgery, "another project" token (foreign ES256 key), stolen-but-expired-shaped token.
// BLOCKED => every forged/absent identity is rejected (401/403) and never reaches game logic. exit 0.
// EXPLOITED => any forgery is accepted (gets a 200 / a game view / a non-auth error). throw => exit 1.
import { anon, call } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const b64 = (o: unknown) => Buffer.from(JSON.stringify(o)).toString("base64url");
const fails: string[] = [];
// A 5xx from the local edge runtime under load (502/503/504/546) is an upstream hiccup, not the function
// accepting a forgery — retry it so a transient error is never misread as an identity bypass.
const TRANSIENT = new Set([502, 503, 504, 546]);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
async function settle<T extends { status: number }>(send: () => Promise<T>, tries = 5): Promise<T> {
  let r = await send();
  for (let i = 0; i < tries && TRANSIENT.has(r.status); i++) { await sleep(300 * (i + 1)); r = await send(); }
  return r;
}
// An identity attack is BLOCKED iff the function denied it: 401/403 (or at worst a non-200 that is not a game view).
const blocked = (name: string, status: number, body: any) => {
  const ok = (status === 401 || status === 403) && !(body && body.id) && body?.you === undefined;
  console.log(`${ok ? "ok  " : "FAIL"} ${name} status=${status} body=${JSON.stringify(body)}`);
  if (!ok) fails.push(`${name}: accepted a forged/absent identity (status=${status}, body=${JSON.stringify(body)})`);
};

// raw POST so we can send a totally missing / malformed Authorization header
async function raw(headers: Record<string, string>) {
  const r = await fetch(`${URL_}/functions/v1/game`, {
    method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify({ action: "create" }),
  });
  let j: any = null; try { j = await r.json(); } catch { /* */ }
  return { status: r.status, body: j };
}

const now = Math.floor(Date.now() / 1000);
const header = (alg: string) => b64({ alg, typ: "JWT", kid: "b81269f1-21d8-4f2e-b719-c2240a840d90" });
const claims = (over: Record<string, unknown> = {}) =>
  b64({ iss: `${URL_}/auth/v1`, sub: "00000000-0000-4000-8000-000000000000", aud: "authenticated", role: "authenticated", exp: now + 3600, iat: now, ...over });

// 0) baseline: a *real* anon token is accepted (so a "blocked" result below means the control works, not that the fn is down)
{
  const t = await anon();
  const r = await settle(() => call(t, { action: "create", color: "white" }));
  console.log(`ok   baseline real-token create status=${r.status}`);
  if (r.status !== 200 || !r.body?.id) fails.push(`baseline real anon token did NOT work (status=${r.status}) — test harness/stack problem`);
}

// 1) no Authorization header at all
blocked("no-auth-header (apikey only)", ...Object.values(await settle(() => raw({ apikey: KEY }))) as [number, any]);
// 2) no auth and no apikey
blocked("no-auth-no-apikey", ...Object.values(await settle(() => raw({}))) as [number, any]);
// 3) publishable key used AS a bearer token (common confusion / "it's a key, right?")
{ const r = await settle(() => call(KEY, { action: "create" })); blocked("publishable-key-as-bearer", r.status, r.body); }
// 4) the apikey header carries the publishable key but bearer is the publishable key too
blocked("publishable-both-headers", ...Object.values(await settle(() => raw({ apikey: KEY, Authorization: `Bearer ${KEY}` }))) as [number, any]);
// 5) structurally-garbage bearer
{ const r = await settle(() => call("not.a.jwt", { action: "create" })); blocked("garbage-bearer", r.status, r.body); }

// 6) tampered signature on an otherwise real token.
//    NB: flip a BYTE of the decoded signature, not the last base64url char. For a 64-byte ES256 signature the
//    final base64url char carries only 2 significant bits (the low 4 are padding), so swapping A<->B there is a
//    no-op that leaves the signature valid — a flaky "exploit". XOR-ing the first signature byte always changes it.
{
  const real = await anon();
  const [h, p, s] = real.split(".");
  const sig = Buffer.from(s, "base64url");
  sig[0] ^= 0xff;
  const tampered = `${h}.${p}.${sig.toString("base64url")}`;
  const r = await settle(() => call(tampered, { action: "create" }));
  blocked("tampered-signature", r.status, r.body);
}
// 7) tampered payload: take real header+sig but swap in a chosen sub (impersonate another uid) — sig no longer matches
{
  const real = await anon();
  const [h, , s] = real.split(".");
  const forged = `${h}.${claims({ sub: "11111111-1111-4111-8111-111111111111" })}.${s}`;
  const r = await settle(() => call(forged, { action: "create" }));
  blocked("tampered-payload-sub", r.status, r.body);
}
// 8) alg=none forgery (classic JWT bypass)
{ const r = await settle(() => call(`${header("none")}.${claims()}.`, { action: "create" })); blocked("alg-none", r.status, r.body); }
// 9) alg=none with empty-but-present signature variant
{ const r = await settle(() => call(`${b64({ alg: "none", typ: "JWT" })}.${claims()}.AAAA`, { action: "create" })); blocked("alg-none-fakesig", r.status, r.body); }
// 10) HS256 forgery signed with the PUBLIC publishable key as if it were the secret (alg-confusion attempt)
{
  const crypto = await import("node:crypto");
  const data = `${b64({ alg: "HS256", typ: "JWT" })}.${claims()}`;
  const sig = crypto.createHmac("sha256", KEY).update(data).digest("base64url");
  const r = await settle(() => call(`${data}.${sig}`, { action: "create" }));
  blocked("hs256-alg-confusion", r.status, r.body);
}
// 11) "another project" / foreign-issuer token: real ES256 structure but signed by a key we generated ourselves
{
  const crypto = await import("node:crypto");
  const { privateKey } = crypto.generateKeyPairSync("ec", { namedCurve: "P-256" });
  const data = `${header("ES256")}.${claims()}`;
  const sig = crypto.sign("sha256", Buffer.from(data), { key: privateKey, dsaEncoding: "ieee-p1363" }).toString("base64url");
  const r = await settle(() => call(`${data}.${sig}`, { action: "create" }));
  blocked("foreign-es256-key", r.status, r.body);
}
// 12) expired-shaped token (past exp). Cannot sign a genuine expired token without the secret, so this doubles as a
//     forgery; a real expired token is rejected by the same auth-server verification (exp claim). Must still be denied.
{
  const real = await anon();
  const [h, , s] = real.split(".");
  const r = await settle(() => call(`${h}.${claims({ exp: now - 10, iat: now - 3610 })}.${s}`, { action: "create" }));
  blocked("expired-shaped", r.status, r.body);
}

if (fails.length) { console.error(`\n${fails.length} EXPLOITED:\n` + fails.join("\n")); process.exit(1); }
console.log("\nall identity forgeries BLOCKED");
process.exit(0);
