// RED TEAM / injection #1 — SQL injection through PostgREST filter values / select / order, and through the
// edge function's `code` field. PostgREST parameterises values, but a mistake would surface as a SQL error
// (500 with a postgres message) or as rows from a game the attacker does not sit in.
// Attack: C (anon, outsider) sends classic injection payloads in filter values, in the embedded-resource
//         `select`, and in `order`; then sends SQL metacharacters in the edge function's room code.
// EXIT 0 = every attempt is parameterised/rejected (no leaked rows, no raw SQL error). throw / EXIT 1 = a
//         query returned another player's row OR a raw SQL error leaked the backend.
import { anon, call } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";

// a real game owned by A+B that C must never see. Retry absorbs transient edge WORKER_LIMIT (546) under load.
async function callRetry(tok: string, body: unknown, want: (b: any) => boolean): Promise<any> {
  for (let i = 0; i < 6; i++) { const r = await call(tok, body); if (r.status === 200 && want(r.body)) return r.body; await new Promise((res) => setTimeout(res, 1500)); }
  throw new Error("setup failed after retries: " + JSON.stringify(body));
}
const A = await anon(), B = await anon(), C = await anon();
const created = await callRetry(A, { action: "create", color: "white" }, (b) => !!b?.id);
const gid = created.id as string, code = created.code as string;
await callRetry(B, { action: "join", code }, (b) => b?.you === "black");

const h = { apikey: KEY, Authorization: `Bearer ${C}`, "Content-Type": "application/json" } as Record<string, string>;
const leaks: string[] = [];

const payloads = [
  `rest/v1/games?select=*&code=eq.${encodeURIComponent(`' OR '1'='1`)}`,
  `rest/v1/games?select=*&code=eq.${encodeURIComponent(`'; DROP TABLE public.games;--`)}`,
  `rest/v1/games?select=*&code=in.(${encodeURIComponent(`'${code}'`)})`,
  `rest/v1/games?select=*&id=eq.${encodeURIComponent(`${gid}) OR (1=1`)}`,
  `rest/v1/games?select=*&or=(code.eq.${code},version.gte.0)`,                 // try to OR past RLS
  `rest/v1/games?select=*,private_positions:positions(*)`,                      // embed the hidden table
  `rest/v1/games?select=*&order=${encodeURIComponent("(select state from private.positions limit 1)")}`,
  `rest/v1/games?select=*&code=like.*`,
  `rest/v1/games?select=version.sum()`,                                         // aggregate to leak existence
];

for (const path of payloads) {
  const r = await fetch(`${URL_}/${path}`, { headers: h });
  const t = await r.text();
  console.log(`  [${r.status}] ${path.slice(0, 90)} -> ${t.slice(0, 90)}`);
  // a leaked SQL error gives the game away (postgres error structure, table/column names, syntax errors)
  if (/syntax error|permission denied|relation .* does not exist|PGRST\d{3}.*(private|positions)/i.test(t) && r.status >= 500) {
    // PGRST 4xx structured errors are fine (expected); only a 500 with raw SQL is a real leak
    leaks.push(`raw SQL error: ${path} -> ${t.slice(0, 160)}`);
  }
  let rows: unknown[] = []; try { const p = JSON.parse(t); if (Array.isArray(p)) rows = p; } catch { /* */ }
  if (r.status >= 200 && r.status < 300 && rows.length > 0) leaks.push(`leaked ${rows.length} row(s): ${path} -> ${t.slice(0, 160)}`);
}

// injection through the edge function's room code (must be rejected by the regex before any SQL)
for (const bad of [`AAAAAA' OR '1'='1`, `'; DROP--`, `A' UNION SELECT`, `${code}' --`]) {
  const r = await call(C, { action: "join", code: bad });
  console.log(`  join code=${JSON.stringify(bad)} -> [${r.status}] ${JSON.stringify(r.body).slice(0, 60)}`);
  if (r.status === 200) leaks.push(`edge function accepted injected code ${JSON.stringify(bad)}`);
}

if (leaks.length) throw new Error("EXPLOITED injection:\n" + leaks.join("\n"));
console.log("BLOCKED: PostgREST parameterises all filters; no row leak and no raw SQL error; edge function rejects injected codes");
process.exit(0);
