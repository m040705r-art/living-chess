// RED TEAM / surface #1 — is the `game` function the ONLY reachable door, and does path trickery reach more?
// The model says "every change goes through the edge function". If other functions are deployed, or the
// gateway lets you reach internal services by path manipulation, that is extra attack surface.
// Attack: C (anon) probes other plausible function names and path-traversal variants, and probes the auth
//         admin endpoint and the postgres-meta / pg endpoints that must never be exposed.
// EXIT 0 = nothing extra answers usefully (only `game` works; admin/meta are unreachable).
// throw / EXIT 1 = some other function or privileged endpoint responds as if usable.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const C = await anon();
const h = { apikey: KEY, Authorization: `Bearer ${C}`, "Content-Type": "application/json" } as Record<string, string>;

const leaks: string[] = [];

// the real game function must exist (positive control FIRST, before we hammer the worker with 404 probes;
// one retry absorbs a transient edge-runtime worker recycle, which is not a security condition)
{
  let status = 0;
  for (let i = 0; i < 3 && status !== 200; i++) {
    const r = await fetch(`${URL_}/functions/v1/game`, { method: "POST", headers: h, body: JSON.stringify({ action: "create", color: "white" }) });
    status = r.status;
    if (status !== 200) await new Promise((res) => setTimeout(res, 1500));
  }
  console.log(`  POST /functions/v1/game (control) -> [${status}]`);
  if (status !== 200) throw new Error("CONTROL FAILED: the game function did not accept a valid call: " + status);
}

// other function names that would be interesting if they existed
const fnNames = ["admin", "service", "internal", "debug", "_internal", "game-admin", "games", "reset", "seed", "rpc", "..%2f..%2fgame"];
for (const n of fnNames) {
  const r = await fetch(`${URL_}/functions/v1/${n}`, { method: "POST", headers: h, body: "{}" });
  const t = await r.text();
  console.log(`  POST /functions/v1/${n} -> [${r.status}] ${t.slice(0, 80)}`);
  // 200 from a function other than game would be surprising; any non-404/non-401 that returns our-game-like data is a flag
  if (r.status === 200) leaks.push(`/functions/v1/${n} answered 200: ${t.slice(0, 120)}`);
}

// privileged service endpoints that must never be reachable with only the publishable key + anon token
const privileged: [string, string][] = [
  ["GET", "auth/v1/admin/users"],            // GoTrue admin API (service role only)
  ["GET", "pg/"],                            // postgres-meta
  ["GET", "rest/v1/rpc/game_state?p_game=00000000-0000-0000-0000-000000000000"],  // service-role-only rpc
];
for (const [method, path] of privileged) {
  const r = await fetch(`${URL_}/${path}`, { method, headers: h });
  const t = await r.text();
  console.log(`  ${method} /${path} -> [${r.status}] ${t.slice(0, 80)}`);
  if (r.status === 200 && t.length > 2 && !t.startsWith("[]")) leaks.push(`${path} answered 200 with data: ${t.slice(0, 120)}`);
}

if (leaks.length) throw new Error("EXPLOITED extra surface:\n" + leaks.join("\n"));
console.log("BLOCKED: only the game function is usable; other functions and privileged endpoints are not reachable");
process.exit(0);
