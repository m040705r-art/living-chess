// RED TEAM / authz #1 — direct REST table writes & reads on public.games
// Attack: as an outsider (user token AND bare publishable key) try to SELECT/INSERT/UPDATE/PATCH/DELETE
//         public.games directly, bypassing the edge function. Intended model: clients never write tables,
//         and anon cannot even read games.
// EXIT 0 = all blocked. throw = any write/read of the table succeeded.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";

function hdr(token?: string) {
  const h: Record<string, string> = { apikey: KEY, "Content-Type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

const tok = await anon();       // victim: creates a game
const reader = await anon();     // attacker: sits in NO game, so any row it reads is someone else's

// A legitimate game to aim the writes at (created through the proper door).
const created = await fetch(`${URL_}/functions/v1/game`, {
  method: "POST", headers: hdr(tok), body: JSON.stringify({ action: "create", color: "white" }),
}).then((r) => r.json());
const gid = created.id as string;
if (!gid) throw new Error("setup failed: could not create a game: " + JSON.stringify(created));

type Probe = { name: string; method: string; path: string; token?: string; body?: string };
const probes: Probe[] = [
  // reads — `reader` sits in no game, so ANY row it gets back is another user's data (a real leak).
  { name: "select games (bare publishable key / anon role)", method: "GET", path: `rest/v1/games?select=*` },
  { name: "select all games (non-member authenticated role)", method: "GET", path: `rest/v1/games?select=*`, token: reader },
  { name: "select the victim's game by id (non-member)", method: "GET", path: `rest/v1/games?select=*&id=eq.${gid}`, token: reader },
  // writes with user token
  { name: "insert games (user token)", method: "POST", path: `rest/v1/games`, token: tok, body: JSON.stringify({ code: "ZZZZZZ" }) },
  { name: "update games (user token)", method: "PATCH", path: `rest/v1/games?id=eq.${gid}`, token: tok, body: JSON.stringify({ status: "white_won" }) },
  { name: "delete games (user token)", method: "DELETE", path: `rest/v1/games?id=eq.${gid}`, token: tok },
  // writes with bare publishable key (anon role)
  { name: "insert games (bare key)", method: "POST", path: `rest/v1/games`, body: JSON.stringify({ code: "YYYYYY" }) },
  { name: "update games (bare key)", method: "PATCH", path: `rest/v1/games?id=eq.${gid}`, body: JSON.stringify({ status: "draw" }) },
  { name: "delete games (bare key)", method: "DELETE", path: `rest/v1/games?id=eq.${gid}` },
];

const leaks: string[] = [];
for (const p of probes) {
  const r = await fetch(`${URL_}/${p.path}`, {
    method: p.method,
    headers: { ...hdr(p.token), Prefer: "return=representation" },
    body: p.body,
  });
  const text = await r.text();
  // A write/read is "successful" only on a 2xx. 401/403/404 are the intended blocks.
  if (r.status >= 200 && r.status < 300) {
    // For the reads, 200 with [] is the RLS-filtered empty set — NOT a leak. A leak is a non-empty row set.
    let rows: unknown = null;
    try { rows = JSON.parse(text); } catch { /* */ }
    const nonEmpty = Array.isArray(rows) ? rows.length > 0 : text.trim() !== "" && text.trim() !== "[]";
    if (p.method === "GET") {
      if (nonEmpty) leaks.push(`${p.name} -> 200 with rows: ${text.slice(0, 200)}`);
    } else {
      leaks.push(`${p.name} -> ${r.status} ${text.slice(0, 200)}`);
    }
  }
  console.log(`  [${r.status}] ${p.name}`);
}

if (leaks.length) throw new Error("EXPLOITED: direct table access succeeded:\n" + leaks.join("\n"));
console.log("BLOCKED: no direct REST read/write of public.games succeeded");
process.exit(0);
