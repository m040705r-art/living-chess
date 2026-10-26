// RED TEAM / authz #4 — read / enumerate games you do not sit in (RLS + PostgREST operators)
// Attack: A creates a room, B joins (both seats filled). A third player C, knowing the room id AND the
//         room code, tries every PostgREST trick to read the row or enumerate rooms:
//         eq on id, eq/ilike on code, or=, in., not., and a bare "list everything". RLS policy only
//         lets a player read a game where they are white or black.
// Positive control: A (a real member) MUST be able to read the row — otherwise the test proves nothing.
// EXIT 0 = C sees nothing, A sees the row. throw = C read or enumerated any row.
import { anon } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const h = (t: string) => ({ apikey: KEY, Authorization: `Bearer ${t}`, "Content-Type": "application/json" });

const A = await anon(), B = await anon(), C = await anon();

const created = await fetch(`${URL_}/functions/v1/game`, { method: "POST", headers: h(A), body: JSON.stringify({ action: "create", color: "white" }) }).then((r) => r.json());
const gid = created.id as string, code = created.code as string;
if (!gid || !code) throw new Error("setup: create failed " + JSON.stringify(created));
const joined = await fetch(`${URL_}/functions/v1/game`, { method: "POST", headers: h(B), body: JSON.stringify({ action: "join", code }) }).then((r) => r.json());
if (joined.you !== "black") throw new Error("setup: join failed " + JSON.stringify(joined));

// Positive control: member A must read the row.
const mine = await fetch(`${URL_}/rest/v1/games?select=*&id=eq.${gid}`, { headers: h(A) }).then((r) => r.json());
if (!Array.isArray(mine) || mine.length !== 1 || mine[0].id !== gid) {
  throw new Error("CONTROL FAILED: a legitimate member could not read their own game: " + JSON.stringify(mine));
}
console.log("  control ok: member A reads their own row");

// Attacker C's enumeration attempts.
const attacks: string[] = [
  `rest/v1/games?select=*&id=eq.${gid}`,
  `rest/v1/games?select=*&code=eq.${code}`,
  `rest/v1/games?select=*&code=ilike.${code}`,
  `rest/v1/games?select=*&code=ilike.*`,
  `rest/v1/games?select=*&or=(code.eq.${code},id.eq.${gid})`,
  `rest/v1/games?select=*&id=in.(${gid})`,
  `rest/v1/games?select=*&id=not.is.null`,
  `rest/v1/games?select=*&status=eq.playing`,
  `rest/v1/games?select=*&white=not.is.null`,
  `rest/v1/games?select=*`,
  `rest/v1/games?select=*&order=created_at.desc&limit=1000`,
];

const leaks: string[] = [];
for (const path of attacks) {
  const r = await fetch(`${URL_}/${path}`, { headers: h(C) });
  const text = await r.text();
  let rows: unknown[] = [];
  try { const p = JSON.parse(text); if (Array.isArray(p)) rows = p; } catch { /* */ }
  if (r.status >= 200 && r.status < 300 && rows.length > 0) leaks.push(`${path} -> ${rows.length} row(s): ${text.slice(0, 160)}`);
  console.log(`  [${r.status}] rows=${rows.length}  ${path.replace("rest/v1/games?select=*", "games?")}`);
}

if (leaks.length) throw new Error("EXPLOITED: outsider C read/enumerated games:\n" + leaks.join("\n"));
console.log("BLOCKED: RLS hides games from non-members against every PostgREST operator tried");
process.exit(0);
