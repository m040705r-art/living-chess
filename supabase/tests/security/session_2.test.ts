// RED TEAM / session surface #2 — do the per-user rate limits actually trigger (429) when a single account hammers?
// LIMITS in index.ts: create [5/600s], join [20/600s], move [90/60s], resign [10/600s].
// Attack: hammer each action from ONE anonymous account past its limit and demand a 429 "slow_down" (or, for create,
//         the stricter 429 "too_many_rooms" bound). BLOCKED => the account gets throttled. exit 0.
// EXPLOITED => an account can exceed its limit without ever being throttled. throw => exit 1.
import { anon, call } from "../flow.test.ts";
const fails: string[] = [];

// --- move: 90 per 60s. Each validly-shaped move request is counted before game lookup, so bogus games still count.
{
  const t = await anon();
  const game = "99999999-9999-4999-8999-999999999999"; // valid uuid shape, not ours -> 404, but still rate-counted
  let got429 = -1, first429Body: any = null;
  for (let i = 1; i <= 96 && got429 < 0; i++) {
    const r = await call(t, { action: "move", game, move: "e2e4", version: 0 });
    if (r.status === 429) { got429 = i; first429Body = r.body; }
  }
  const ok = got429 > 0 && got429 <= 92; // must throttle at/near the 91st request
  console.log(`${ok ? "ok  " : "FAIL"} move throttled at request #${got429} body=${JSON.stringify(first429Body)}`);
  if (!ok) fails.push(`move: never throttled within 96 requests (got429=${got429}) — limit not enforced`);
}

// --- join: 20 per 600s. Random non-existent codes return 404 no_room but still count toward the limit.
{
  const t = await anon();
  const rand = () => Array.from({ length: 6 }, () => "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"[Math.floor(Math.random() * 32)]).join("");
  let got429 = -1;
  for (let i = 1; i <= 26 && got429 < 0; i++) {
    const r = await call(t, { action: "join", code: rand() });
    if (r.status === 429) got429 = i;
  }
  const ok = got429 > 0 && got429 <= 22;
  console.log(`${ok ? "ok  " : "FAIL"} join throttled at request #${got429}`);
  if (!ok) fails.push(`join: never throttled within 26 requests (got429=${got429}) — limit not enforced`);
}

// --- create: bounded per user. Either the create rate limit [5] or the open-rooms cap [3] must stop a single account
//     from spawning rooms without end. We require a 429 within a handful of creates.
{
  const t = await anon();
  let got429 = -1, kind = "";
  for (let i = 1; i <= 8 && got429 < 0; i++) {
    const r = await call(t, { action: "create", color: "white" });
    if (r.status === 429) { got429 = i; kind = r.body?.error; }
  }
  const ok = got429 > 0 && got429 <= 6;
  console.log(`${ok ? "ok  " : "FAIL"} create bounded at request #${got429} (${kind})`);
  if (!ok) fails.push(`create: a single account created 8 rooms with no 429 — per-user create bound missing`);
}

if (fails.length) { console.error(`\n${fails.length} EXPLOITED:\n` + fails.join("\n")); process.exit(1); }
console.log("\nall single-account rate limits BLOCKED (throttling triggers)");
process.exit(0);
