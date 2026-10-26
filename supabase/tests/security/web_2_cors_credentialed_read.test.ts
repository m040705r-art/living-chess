// WEB-2  Dangerous CORS combo: reflected attacker origin + Access-Control-Allow-Credentials:true.
// That combo is the only CORS shape that lets a credentialed cross-origin browser read a victim's
// response body.  We verify the function endpoint does NOT reflect the attacker's specific origin
// together with credentials:true.  (The local gateway returns ACAO:* which, WITHOUT credentials,
// cannot be paired with credentials and carries no ambient cookies here -> not usable for theft.)
// BLOCKED => exit 0.  Reflected-origin + credentials => throw (exploited).
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const EVIL = "https://evil.example";
const token = await anon();

async function headers(method: string) {
  const r = await fetch(`${URL_}/functions/v1/game`, {
    method,
    headers: {
      apikey: KEY, Authorization: `Bearer ${token}`, "Content-Type": "application/json", Origin: EVIL,
      ...(method === "OPTIONS" ? { "Access-Control-Request-Method": "POST" } : {}),
    },
    body: method === "POST" ? JSON.stringify({ action: "join", code: "AAAAAA" }) : undefined,
  });
  return {
    status: r.status,
    acao: r.headers.get("access-control-allow-origin"),
    creds: r.headers.get("access-control-allow-credentials"),
  };
}

const pre = await headers("OPTIONS");
const post = await headers("POST");
console.log("preflight", JSON.stringify(pre));
console.log("actual   ", JSON.stringify(post));

for (const h of [pre, post]) {
  // the fatal shape: attacker origin echoed back AND credentials allowed
  if (h.acao === EVIL && (h.creds ?? "").toLowerCase() === "true") {
    throw new Error(`EXPLOITED: function reflects attacker Origin with credentials:true -> ${JSON.stringify(h)}`);
  }
  // also fatal: wildcard WITH credentials would let any origin read if browsers honored it
  if (h.acao === "*" && (h.creds ?? "").toLowerCase() === "true") {
    throw new Error(`EXPLOITED: ACAO:* together with credentials:true on function -> ${JSON.stringify(h)}`);
  }
}
console.log("BLOCKED: no reflected-origin+credentials combo on the game function (ACAO=" + post.acao + ", credentials=" + post.creds + ").");
// natural exit 0 (avoid process.exit while undici keep-alive sockets are closing -> libuv assert on Windows)
