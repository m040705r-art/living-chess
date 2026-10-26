// RED TEAM / logic — race the version check: fire two moves at once on the same version.
// The compare-and-set in game_commit must let AT MOST ONE win; a double-commit (two moves recorded, or the
// version jumping by two, or both responses 200) would be a cheat. Exit 0 if safe; throw on a double-commit.
import { anon, call } from "../flow.test.ts";

let bad = 0;
const check = (name: string, safe: boolean, got: unknown) => {
  console.log(`${safe ? "SAFE   " : "EXPLOIT"}  ${name}  ${JSON.stringify(got)}`);
  if (!safe) bad++;
};

async function freshPlaying() {
  const w = await anon(), b = await anon();
  const c = await call(w, { action: "create", color: "white" });
  const j = await call(b, { action: "join", code: c.body.code });
  if (c.status !== 200 || j.status !== 200) throw new Error("setup failed");
  return { w, b, id: c.body.id, v: j.body.version as number };
}

// --- Round A: two DIFFERENT legal white moves, same version, concurrently.
{
  const { w, id, v } = await freshPlaying();
  const [r1, r2] = await Promise.all([
    call(w, { action: "move", game: id, move: "e2e4", version: v }),
    call(w, { action: "move", game: id, move: "d2d4", version: v }),
  ]);
  const wins = [r1, r2].filter((r) => r.status === 200);
  check("two different moves on one version -> exactly one wins", wins.length === 1, { s1: r1.status, s2: r2.status });
  if (wins.length === 1) {
    check("winner recorded exactly one move", wins[0].body.moves.length === 1 && wins[0].body.version === v + 1, wins[0].body);
  }
}

// --- Round B: the SAME move twice, concurrently (duplicate submit / double-click).
{
  const { w, id, v } = await freshPlaying();
  const [r1, r2] = await Promise.all([
    call(w, { action: "move", game: id, move: "e2e4", version: v }),
    call(w, { action: "move", game: id, move: "e2e4", version: v }),
  ]);
  const wins = [r1, r2].filter((r) => r.status === 200);
  check("same move submitted twice -> exactly one wins", wins.length === 1, { s1: r1.status, s2: r2.status });
  if (wins.length === 1) {
    check("duplicate submit recorded exactly one move", wins[0].body.moves.length === 1 && wins[0].body.version === v + 1, wins[0].body);
  }
}

// --- Round C: both players resign the same game at once (concurrent terminal writes).
{
  const { w, b, id } = await freshPlaying();
  const [r1, r2] = await Promise.all([
    call(w, { action: "resign", game: id }),
    call(b, { action: "resign", game: id }),
  ]);
  const wins = [r1, r2].filter((r) => r.status === 200);
  check("concurrent resigns -> exactly one terminal write", wins.length === 1, { s1: r1.status, s2: r2.status });
}

if (bad) throw new Error(`${bad} race condition(s) produced a double-commit`);
console.log("logic_4: all safe");
process.exit(0);
