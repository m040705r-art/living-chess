// WEB-6  Deployment hardening of the function's HTTP responses.  Authenticated JSON responses must
// not be content-sniffable (X-Content-Type-Options: nosniff) nor stored by shared caches
// (Cache-Control: no-store), and error bodies must be terse codes that never echo server internals.
// BLOCKED => exit 0.  Missing nosniff/no-store or an internals leak in an error body => throw.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const token = await anon();

async function get(body: unknown) {
  const r = await fetch(`${URL_}/functions/v1/game`, {
    method: "POST",
    headers: { apikey: KEY, Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text();
  return { status: r.status, text, nosniff: r.headers.get("x-content-type-options"), cache: r.headers.get("cache-control") };
}

const problems: string[] = [];

// a well-formed but failing request (bad action) and a valid-ish one both go through reply()/fail()
const samples = [
  await get({ action: "nope" }),            // 400 action
  await get({ action: "join", code: "!" }), // 400 code
  await get({ action: "create", color: "white" }), // 200
];
for (const s of samples) {
  console.log(`status=${s.status} nosniff=${s.nosniff} cache=${s.cache} body=${s.text.slice(0, 120)}`);
  if ((s.nosniff ?? "").toLowerCase() !== "nosniff") problems.push(`missing X-Content-Type-Options:nosniff (status ${s.status})`);
  if (!/no-store/i.test(s.cache ?? "")) problems.push(`missing Cache-Control:no-store (status ${s.status})`);
  // internals an error body must never contain
  if (/(stack|at \w+ \(|postgres|pg_|relation \"|syntax error|\/home\/|deno|SUPABASE_|service_role)/i.test(s.text))
    problems.push(`error body leaks internals: ${s.text.slice(0, 160)}`);
}

if (problems.length) throw new Error("EXPLOITED: weak response hardening:\n" + problems.join("\n"));
console.log("BLOCKED: nosniff + no-store present on all responses; error bodies are terse codes.");
// natural exit 0 (avoid process.exit while undici keep-alive sockets are closing -> libuv assert on Windows)
