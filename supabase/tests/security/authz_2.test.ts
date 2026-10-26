// RED TEAM / authz #2 — reach the private schema (positions, rate_limits) through the Data API
// Attack: PostgREST exposes a schema via the Accept-Profile (read) / Content-Profile (write) headers.
//         Try to read private.positions (the hidden chess position = the whole secret) and private.rate_limits,
//         and to write a position row, by naming the private schema in those headers and as public.<table>.
// EXIT 0 = unreachable. throw = the private schema answered with data or accepted a write.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const tok = await anon();
const base = { apikey: KEY, Authorization: `Bearer ${tok}`, "Content-Type": "application/json" };

type Probe = { name: string; method: string; path: string; headers: Record<string, string>; body?: string };
const probes: Probe[] = [
  { name: "read positions via Accept-Profile: private", method: "GET", path: "rest/v1/positions?select=*", headers: { ...base, "Accept-Profile": "private" } },
  { name: "read rate_limits via Accept-Profile: private", method: "GET", path: "rest/v1/rate_limits?select=*", headers: { ...base, "Accept-Profile": "private" } },
  { name: "read positions as public.positions", method: "GET", path: "rest/v1/positions?select=*", headers: base },
  { name: "read rate_limits as public.rate_limits", method: "GET", path: "rest/v1/rate_limits?select=*", headers: base },
  { name: "write positions via Content-Profile: private", method: "POST", path: "rest/v1/positions", headers: { ...base, "Content-Profile": "private" }, body: JSON.stringify({ game_id: "00000000-0000-0000-0000-000000000000", state: {} }) },
  { name: "read positions via ?schema=private query", method: "GET", path: "rest/v1/positions?select=*&schema=private", headers: base },
];

const leaks: string[] = [];
for (const p of probes) {
  const r = await fetch(`${URL_}/${p.path}`, { method: p.method, headers: p.headers, body: p.body });
  const text = await r.text();
  if (r.status >= 200 && r.status < 300) {
    const trimmed = text.trim();
    // empty array = nothing returned; any object/row content from the private schema is a leak
    if (trimmed !== "" && trimmed !== "[]") leaks.push(`${p.name} -> ${r.status} ${trimmed.slice(0, 200)}`);
  }
  console.log(`  [${r.status}] ${p.name}`);
}

if (leaks.length) throw new Error("EXPLOITED: private schema reachable:\n" + leaks.join("\n"));
console.log("BLOCKED: private schema (positions, rate_limits) is not reachable through the Data API");
process.exit(0);
