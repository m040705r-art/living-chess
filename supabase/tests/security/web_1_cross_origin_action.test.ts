// WEB-1  Cross-origin state change from an off-allow-list page.
// Threat: a page on https://evil.example tries to drive the game function with a VALID anon token
// (as a browser would: the Origin header is set by the browser and cannot be forged from JS).
// The function must refuse (403 "origin") BEFORE performing any action, regardless of what CORS
// headers the gateway adds.  BLOCKED => exit 0.  If the action is performed => throw (exploited).
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const EVIL = "https://evil.example";

const token = await anon();
const r = await fetch(`${URL_}/functions/v1/game`, {
  method: "POST",
  headers: { apikey: KEY, Authorization: `Bearer ${token}`, "Content-Type": "application/json", Origin: EVIL },
  body: JSON.stringify({ action: "create", color: "white" }),
});
const acao = r.headers.get("access-control-allow-origin");
const body = await r.json().catch(() => null);
console.log("status", r.status, "ACAO", acao, "body", JSON.stringify(body));

if (r.status === 200 && body?.id) {
  throw new Error(`EXPLOITED: evil origin created a game cross-site -> ${JSON.stringify(body)}`);
}
if (r.status !== 403) {
  throw new Error(`UNEXPECTED: evil origin was not rejected with 403 origin (got ${r.status})`);
}
console.log("BLOCKED: cross-origin action rejected with 403 before any state change (note: gateway still sends ACAO=" + acao + ", but the app refuses the action).");
// natural exit 0 (avoid process.exit while undici keep-alive sockets are closing -> libuv assert on Windows)
