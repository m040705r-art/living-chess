// node supabase/tests/perft.test.ts  - the server's rules must count exactly the known move-tree sizes
import { initial, legalMoves, make, type Position } from "../functions/_shared/chess.ts";

function fen(s: string): Position {
  const [rows, side, cast] = s.split(" ");
  const b = new Array(64).fill(0);
  rows.split("/").forEach((row, i) => {
    let f = 0;
    for (const c of row) {
      if (/\d/.test(c)) { f += +c; continue; }
      const t = "pnbrqk".indexOf(c.toLowerCase()) + 1;
      b[(7 - i) * 8 + f++] = c === c.toUpperCase() ? t : -t;
    }
  });
  let castle = 0;
  if (cast.includes("K")) castle |= 1; if (cast.includes("Q")) castle |= 2; if (cast.includes("k")) castle |= 4; if (cast.includes("q")) castle |= 8;
  return { b, side: side === "w" ? 1 : -1, castle, ep: -1, half: 0, full: 1, seen: [] };
}
function perft(p: Position, d: number): number {
  if (d === 0) return 1;
  let n = 0;
  for (const m of legalMoves(p)) n += perft(make(p, m), d - 1);
  return n;
}
const cases: [string, Position, number, number][] = [
  ["start", initial(), 4, 197281],
  ["kiwipete", fen("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -"), 3, 97862],
  ["pos3", fen("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -"), 4, 43238],
  ["pos4", fen("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq -"), 3, 9467],
  ["pos5", fen("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ -"), 3, 62379],
];
let ok = true;
for (const [name, p, d, want] of cases) {
  const got = perft(p, d);
  console.log(`${name} d${d}: ${got} ${got === want ? "ok" : "FAIL (want " + want + ")"}`);
  if (got !== want) ok = false;
}
process.exit(ok ? 0 : 1);
