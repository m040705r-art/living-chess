// RED TEAM / realtime #1 — can an OUTSIDER read live game data over the Realtime websocket?
// The REST path is RLS-protected (round 1). Realtime is a SEPARATE channel on the same stack. If
// public.games is in the realtime publication and RLS is not enforced on the socket, an outsider who
// subscribes to postgres_changes on public.games would receive every move of every game (moves, code,
// seats) as it happens — a full confidentiality bypass / IDOR that never touches /rest/v1.
// Attack: C (outsider, not in the game) opens the realtime socket with only the publishable key + a
//         fresh anonymous token and subscribes to changes on public.games (wildcard AND id-filtered).
//         A and B then play a move through the edge function (an UPDATE on public.games). If C receives
//         the row, it is exploited.
// EXIT 0 = C receives nothing for a game it does not sit in. throw / EXIT 1 = C received game data.
import { anon, call } from "../flow.test.ts";

const URL_ = process.env.SB_URL ?? "http://127.0.0.1:54321";
const KEY = process.env.SB_KEY ?? "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const WS = `ws://127.0.0.1:54321/realtime/v1/websocket?apikey=${KEY}&vsn=1.0.0`;

const HARD_TIMEOUT = setTimeout(() => { console.error("timeout"); process.exit(1); }, 80_000);

// --- set up a real game that will be mutated. Retry absorbs transient edge-runtime WORKER_LIMIT (546) under
//     load — a resource-limit response, not a security condition — so the realtime check itself is reliable.
async function callRetry(tok: string, body: unknown, want: (b: any) => boolean): Promise<any> {
  for (let i = 0; i < 6; i++) {
    const r = await call(tok, body);
    if (r.status === 200 && want(r.body)) return r.body;
    await new Promise((res) => setTimeout(res, 1500));
  }
  throw new Error("setup failed after retries for " + JSON.stringify(body));
}
const A = await anon(), B = await anon(), C = await anon();
const created = await callRetry(A, { action: "create", color: "white" }, (b) => !!b?.id);
const gid = created.id as string, code = created.code as string;
const joined = await callRetry(B, { action: "join", code }, (b) => b?.you === "black");

// --- open a realtime socket as outsider C and subscribe to changes on public.games
function subscribe(token: string, label: string, received: unknown[], transcript: string[]): Promise<void> {
  return new Promise((resolve) => {
    const ws = new WebSocket(WS);
    let ref = 0;
    const next = () => String(++ref);
    const topics = [
      { topic: `realtime:all-${label}`, pg: [{ event: "*", schema: "public", table: "games" }] },
      { topic: `realtime:one-${label}`, pg: [{ event: "*", schema: "public", table: "games", filter: `id=eq.${gid}` }] },
    ];
    ws.addEventListener("open", () => {
      for (const t of topics) {
        ws.send(JSON.stringify({
          topic: t.topic, event: "phx_join", ref: next(),
          payload: { config: { postgres_changes: t.pg, broadcast: { self: true }, presence: { key: "" } }, access_token: token },
        }));
      }
      // also push the token explicitly (how supabase-js authorizes the socket for RLS)
      ws.send(JSON.stringify({ topic: topics[0].topic, event: "access_token", ref: next(), payload: { access_token: token } }));
      const hb = setInterval(() => { try { ws.send(JSON.stringify({ topic: "phoenix", event: "heartbeat", ref: next(), payload: {} })); } catch { /* */ } }, 15_000);
      (ws as unknown as { _hb: ReturnType<typeof setInterval> })._hb = hb;
    });
    ws.addEventListener("message", (ev) => {
      const text = typeof ev.data === "string" ? ev.data : "";
      let msg: any = null; try { msg = JSON.parse(text); } catch { /* */ }
      if (!msg) return;
      // a postgres_changes payload carries the actual row under payload.data.record / .old_record
      if (msg.event === "postgres_changes" || msg.event === "INSERT" || msg.event === "UPDATE" || msg.event === "DELETE") {
        const rec = msg?.payload?.data?.record ?? msg?.payload?.record ?? msg?.payload?.data?.old_record ?? null;
        const txt = JSON.stringify(msg.payload ?? msg);
        if (rec || txt.includes(code) || txt.includes(gid)) {
          received.push({ label, event: msg.event, snippet: txt.slice(0, 240) });
        }
      }
      // capture handshake evidence: phx_reply (join ack/err) and realtime "system" (postgres_changes sub status)
      if (msg.event === "phx_reply" || msg.event === "system" || msg.event === "presence_state") {
        transcript.push(`[${label}] ${msg.event} ${JSON.stringify(msg.payload).slice(0, 160)}`);
      }
    });
    ws.addEventListener("error", () => resolve());
    setTimeout(() => { try { clearInterval((ws as any)._hb); ws.close(); } catch { /* */ } resolve(); }, 12_000);
  });
}

const cLeaks: unknown[] = [];   // what the OUTSIDER received  -> must stay empty
const bRows: unknown[] = [];    // what a MEMBER received      -> positive control (informational)
const transcript: string[] = []; // handshake evidence (join acks, subscription status)

const cDone = subscribe(C, "C-outsider", cLeaks, transcript);
const bDone = subscribe(B, "B-member", bRows, transcript);

// give both sockets time to finish joining before we mutate the row
await new Promise((r) => setTimeout(r, 3000));

// mutate public.games: play a legal first move (UPDATE: moves, version, updated_at)
const mv = await call(A, { action: "move", game: gid, move: "e2e4", version: joined.version });
if (mv.status !== 200) console.log("  note: move returned " + mv.status + " " + JSON.stringify(mv.body));
// and resign to force a second UPDATE (status change), maximising the chance of catching a leak
await new Promise((r) => setTimeout(r, 500));
await call(B, { action: "resign", game: gid });

await Promise.all([cDone, bDone]);
clearTimeout(HARD_TIMEOUT);

console.log("  --- realtime handshake transcript (evidence the sockets actually connected/subscribed) ---");
for (const line of transcript) console.log("  " + line);
console.log("  --------------------------------------------------------------------------------------");
console.log(`  member B received ${bRows.length} change event(s) (positive control / informational)`);
console.log(`  outsider C received ${cLeaks.length} change event(s)`);

if (cLeaks.length > 0) {
  throw new Error("EXPLOITED: outsider received live game data over Realtime:\n" + JSON.stringify(cLeaks, null, 2));
}
console.log("BLOCKED: outsider receives no public.games changes over Realtime (RLS enforced or table not published)");
process.exit(0);
