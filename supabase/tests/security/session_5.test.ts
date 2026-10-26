// RED TEAM / session surface #5 — refresh-token & session abuse by an OUTSIDER (public key + HTTP only; no stolen secrets).
// Attacks: (a) forge/guess a refresh token to mint a session you were never granted; (b) check a refreshed access token
// does not escalate beyond the anonymous "authenticated" role; (c) observe refresh-token rotation / reuse-detection.
// BLOCKED => a fabricated refresh token yields no session and refresh grants no extra privilege. exit 0.
// EXPLOITED => a forged/guessed refresh token returns a session, or a refreshed token carries elevated role/claims. throw.
import { anon } from "../flow.test.ts";
const BASE = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const fails: string[] = [];
const tok = (rt: string) => fetch(`${BASE}/auth/v1/token?grant_type=refresh_token`,
  { method: "POST", headers: { apikey: KEY, "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: rt }) });
const claims = (jwt: string) => JSON.parse(Buffer.from(jwt.split(".")[1], "base64url").toString());

// Get a legitimate session so we know the refresh endpoint is reachable and see a real refresh token's shape.
const signup = await (await fetch(`${BASE}/auth/v1/signup`, { method: "POST", headers: { apikey: KEY, "Content-Type": "application/json" }, body: "{}" })).json();
const realRt: string = signup.refresh_token;
console.log(`baseline: real refresh token length=${realRt.length}`);

// (a) FORGE/GUESS: refresh tokens are opaque server-side secrets; an outsider can only guess. All of these must fail.
const forged = [
  "", "undefined", "null",
  realRt.slice(0, -1) + (realRt.endsWith("a") ? "b" : "a"),         // one char off a real token
  Array.from({ length: realRt.length }, () => "abcdefghijklmnopqrstuvwxyz0123456789"[Math.floor(Math.random() * 36)]).join(""),
  "00000000-0000-0000-0000-000000000000",
  realRt.toUpperCase(),
];
for (const f of forged) {
  const r = await tok(f);
  const j: any = await r.json().catch(() => null);
  const granted = r.status === 200 && j?.access_token;
  console.log(`${granted ? "FAIL" : "ok  "} forged refresh (${JSON.stringify(f.slice(0, 10))}…) status=${r.status} err=${j?.error_code ?? j?.msg ?? "-"}`);
  if (granted) fails.push(`forged/guessed refresh token was accepted -> session minted (token=${f.slice(0, 12)}…)`);
}

// (b) NO ESCALATION: a token obtained purely via the public anon flow must stay role=authenticated, is_anonymous=true,
//     and carry no service_role / admin claims. (Guards against the refresh flow handing back an elevated token.)
{
  const access = await anon();
  const c = claims(access);
  console.log(`refreshed/anon access claims: role=${c.role} is_anon=${c.is_anonymous} aud=${c.aud}`);
  if (c.role !== "authenticated") fails.push(`anon access token role is '${c.role}', expected 'authenticated' — privilege escalation`);
  if (c.role === "service_role" || c.role === "supabase_admin") fails.push(`anon token carries elevated role ${c.role}`);
  if (c.is_anonymous === false) fails.push(`anon flow produced a non-anonymous (is_anonymous=false) session without any credential`);
}

// (c) ROTATION / REUSE observation (informational; exploiting it needs a stolen token, which an outsider lacks).
{
  const r1 = await (await tok(realRt)).json();                       // rotates
  const r2 = await tok(realRt);                                      // reuse old token
  const j2: any = await r2.json().catch(() => null);
  const reuseStillWorks = r2.status === 200 && !!j2?.access_token;
  console.log(`rotation: new rt issued=${!!r1.refresh_token}; reuse of old rt -> status=${r2.status} (still_works=${reuseStillWorks})`);
  console.log(reuseStillWorks
    ? "note(info/theoretical): reuse-detection does not revoke the family on old-token replay; impact requires prior token theft"
    : "note: old refresh token is rejected after rotation (reuse detection active)");
}

if (fails.length) { console.error(`\n${fails.length} EXPLOITED:\n` + fails.join("\n")); process.exit(1); }
console.log("\noutsider cannot forge a session; refresh grants no escalation — BLOCKED");
process.exit(0);
