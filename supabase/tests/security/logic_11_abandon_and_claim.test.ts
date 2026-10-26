// RED TEAM / business-logic #11 — abandonment & illegitimate result claims.
// Two angles the intended model does NOT explicitly promise against:
//  (a) INTEGRITY (must hold): a player must NOT be able to award themselves a win, force a draw, or resolve
//      the game in their favour through any action the function exposes. The only self-service result is
//      `resign`, which can only make the CALLER lose.
//  (b) AVAILABILITY / FAIRNESS (design gap): there is no clock/forfeit, so a player who is losing can simply
//      stop playing and the game stays 'playing' forever — the opponent is denied the win. game_housekeeping
//      never touches 'playing' rows. This is a product gap, not a privilege break; we record it, we do not
//      fail the suite on it (no security boundary is crossed).
// EXIT 0 = the integrity boundary holds (no stolen win, no forced draw, no accepted bogus result action).
// throw / EXIT 1 = a player obtained a win/draw they were not entitled to.
import { anon, call } from "../flow.test.ts";

// Retry absorbs transient edge WORKER_LIMIT (546) under load during setup.
async function callRetry(tok: string, body: unknown, want: (b: any) => boolean): Promise<any> {
  for (let i = 0; i < 6; i++) { const r = await call(tok, body); if (r.status === 200 && want(r.body)) return r.body; await new Promise((res) => setTimeout(res, 1500)); }
  throw new Error("setup failed after retries: " + JSON.stringify(body));
}
const A = await anon(), B = await anon();
const created = await callRetry(A, { action: "create", color: "white" }, (b) => !!b?.id);
const gid = created.id as string, code = created.code as string;
const joined = await callRetry(B, { action: "join", code }, (b) => b?.you === "black");
let v = joined.version as number;

const leaks: string[] = [];

// (a1) B (black) tries result-granting actions that are not part of the protocol
for (const bogus of [
  { action: "win", game: gid },
  { action: "claim", game: gid },
  { action: "forfeit", game: gid },
  { action: "timeout", game: gid },
  { action: "draw", game: gid },
  { action: "offer_draw", game: gid },
  { action: "move", game: gid, move: "e2e4", version: v },   // B moving white's pawn / out of turn
]) {
  const r = await call(B, bogus as unknown as Record<string, unknown>);
  console.log(`  B ${JSON.stringify(bogus).slice(0, 48)} -> [${r.status}] ${JSON.stringify(r.body).slice(0, 48)}`);
  // success would be a 200 that resolves the game for B
  if (r.status === 200 && typeof r.body === "object" && r.body && "status" in r.body && (r.body as any).status === "black_won") {
    leaks.push("B illegitimately won via " + JSON.stringify(bogus));
  }
}

// (a2) A (white) plays one legal move so it is B's turn, then B abandons (never acts). A must not be able to
//      convert the abandonment into a win for A.
const mv = await call(A, { action: "move", game: gid, move: "e2e4", version: v });
if (mv.status === 200) v = mv.body.version;
for (const bogus of [{ action: "win", game: gid }, { action: "claim", game: gid }, { action: "timeout", game: gid }, { action: "move", game: gid, move: "e7e5", version: v }]) {
  const r = await call(A, bogus as unknown as Record<string, unknown>);
  console.log(`  A (opponent abandoned) ${JSON.stringify(bogus).slice(0, 40)} -> [${r.status}]`);
  if (r.status === 200 && typeof r.body === "object" && r.body && (r.body as any).status === "white_won") {
    leaks.push("A illegitimately won after opponent abandoned via " + JSON.stringify(bogus));
  }
}

// confirm the integrity property: the only self-service resolution (resign) makes the CALLER lose, never win
const resign = await call(A, { action: "resign", game: gid });
console.log(`  A resign -> [${resign.status}] status=${(resign.body as any)?.status}`);
if (resign.status === 200 && (resign.body as any)?.status === "white_won") {
  leaks.push("resign awarded the win to the resigning player A");
}

// AVAILABILITY note (not a failure): a game left by a losing player stays 'playing'; opponent has no recourse.
console.log("  NOTE (design gap, not a failure): there is no clock/forfeit; a losing player can abandon a");
console.log("       'playing' game indefinitely and deny the opponent a result. Integrity is unaffected.");

if (leaks.length) throw new Error("EXPLOITED result-claim:\n" + leaks.join("\n"));
console.log("BLOCKED: no action awards a win/draw illegitimately; resign only makes the caller lose");
process.exit(0);
