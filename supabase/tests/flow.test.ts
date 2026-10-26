// node supabase/tests/flow.test.ts  - against the local stack (npx supabase start + functions serve)
// Two anonymous players: create a room, join by code, play Scholar's mate, and check each step's answer.
const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";   // local dev stack only

export async function anon(): Promise<string> {
  const r = await fetch(`${URL_}/auth/v1/signup`, { method: "POST", headers: { apikey: KEY, "Content-Type": "application/json" }, body: "{}" });
  const j = await r.json();
  if (!j.access_token) throw new Error("anon sign-in failed: " + JSON.stringify(j));
  return j.access_token;
}
export async function call(token: string, body: unknown, extra: Record<string, string> = {}) {
  const r = await fetch(`${URL_}/functions/v1/game`, {
    method: "POST", headers: { apikey: KEY, Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...extra },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
  let j: any = null; try { j = await r.json(); } catch { /* empty */ }
  return { status: r.status, body: j };
}

const fails: string[] = [];
const expect = (name: string, cond: boolean, got: unknown) => { console.log(`${cond ? "ok  " : "FAIL"} ${name}`); if (!cond) fails.push(name + " -> " + JSON.stringify(got)); };

if (import.meta.url === `file:///${process.argv[1].replace(/\\/g, "/")}` || process.argv[1].endsWith("flow.test.ts")) {
  const a = await anon(), b = await anon();
  const c = await call(a, { action: "create", color: "white" });
  expect("create", c.status === 200 && /^[A-HJ-NP-Z2-9]{6}$/.test(c.body.code) && c.body.you === "white", c);
  const j = await call(b, { action: "join", code: c.body.code });
  expect("join", j.status === 200 && j.body.you === "black" && j.body.opponent_joined, j);
  const game = c.body.id;
  let v = j.body.version;
  for (const [tok, mv] of [[a, "e2e4"], [b, "e7e5"], [a, "f1c4"], [b, "b8c6"], [a, "d1h5"], [b, "g8f6"], [a, "h5f7"]] as [string, string][]) {
    const r = await call(tok, { action: "move", game, move: mv, version: v });
    expect("move " + mv, r.status === 200, r);
    v = r.body.version;
  }
  const end = await call(b, { action: "move", game, move: "a7a6", version: v });
  expect("no move after mate", end.status === 409, end);
  const read = await fetch(`${URL_}/rest/v1/games?select=status,result_reason,moves&id=eq.${game}`, { headers: { apikey: KEY, Authorization: `Bearer ${a}` } }).then((r) => r.json());
  expect("result white_won by checkmate", read[0]?.status === "white_won" && read[0]?.result_reason === "checkmate", read);
  console.log(fails.length ? `\n${fails.length} FAILED\n` + fails.join("\n") : "\nall passed");
  process.exit(fails.length ? 1 : 0);
}
