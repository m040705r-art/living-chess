// For manual Unity tests against the local stack: join a room by code and answer with the given moves.
//   node supabase/tests/opponent.ts CODE e7e5 b8c6 ...
import { anon, call } from "./flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";   // local dev stack only
const [code, ...replies] = process.argv.slice(2);
const tok = await anon();
const j = await call(tok, { action: "join", code });
console.log("join", j.status, j.body?.you ?? j.body?.error);
let n = 0;
for (const mv of replies) {
  for (let i = 0; i < 90; i++) {
    const g = await fetch(`${URL_}/rest/v1/games?select=moves,version&id=eq.${j.body.id}`, { headers: { apikey: KEY, Authorization: `Bearer ${tok}` } }).then((r) => r.json());
    if (g[0].moves.length > n && g[0].moves.length % 2 === 1) {
      const r = await call(tok, { action: "move", game: j.body.id, move: mv, version: g[0].version });
      console.log("move", mv, r.status, r.body?.error ?? "");
      n = g[0].moves.length + 1;
      break;
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
}
