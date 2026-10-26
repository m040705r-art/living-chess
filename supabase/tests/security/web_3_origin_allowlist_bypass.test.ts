// WEB-3  Allow-list bypass with near-miss Origins.  A browser sends the real Origin; an attacker who
// controls a look-alike host (suffix/prefix/scheme tricks) must NOT pass the function's allow-list.
// For every variant the function must answer 403 "origin" and perform no action.
// BLOCKED => exit 0.  Any variant that is accepted (status 200 or a non-403 that lets the action run) => throw.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";

const VARIANTS = [
  "https://m040705r-art.github.io.evil.com", // suffix attack
  "https://evilm040705r-art.github.io",      // prefix attack
  "http://m040705r-art.github.io",           // downgraded scheme (allow-list is https)
  "https://m040705r-art.github.io.",         // trailing dot
  "https://M040705R-ART.GITHUB.IO",          // case
  "null",                                    // sandboxed iframe / file://
  "https://m040705r-art.github.io:8765",     // extra port
];

const token = await anon();
const leaked: string[] = [];
for (const origin of VARIANTS) {
  const r = await fetch(`${URL_}/functions/v1/game`, {
    method: "POST",
    headers: { apikey: KEY, Authorization: `Bearer ${token}`, "Content-Type": "application/json", Origin: origin },
    body: JSON.stringify({ action: "create", color: "black" }),
  });
  const body = await r.json().catch(() => null);
  const acao = r.headers.get("access-control-allow-origin");
  console.log(`origin=${origin} -> status=${r.status} acao=${acao} body=${JSON.stringify(body)}`);
  if (r.status === 200 && body?.id) leaked.push(`${origin} created a game`);
  if (r.status !== 403) leaked.push(`${origin} not rejected (status ${r.status})`);
  // reflecting the exact near-miss origin back would also be a problem
  if (acao === origin && origin !== "null") leaked.push(`${origin} reflected in ACAO`);
}
if (leaked.length) throw new Error("EXPLOITED: allow-list bypassed:\n" + leaked.join("\n"));
console.log("BLOCKED: every near-miss origin was rejected with 403 and never reflected.");
// natural exit 0 (avoid process.exit while undici keep-alive sockets are closing -> libuv assert on Windows)
