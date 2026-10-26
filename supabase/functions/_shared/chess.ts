// The rules of chess for the server (a port of Assets/Chess/Code/Runtime/ChessRules.cs). The server is the only
// authority: a client's move is applied only if it is in legalMoves() of the stored position.
// Plain TypeScript (no Deno/Node APIs) so the same file runs in the Edge Function and in the node tests.
// Squares 0..63 = rank * 8 + file (a1 = 0). Pieces: 1 pawn .. 6 king, white > 0, black < 0.

export const PAWN = 1, KNIGHT = 2, BISHOP = 3, ROOK = 4, QUEEN = 5, KING = 6;
const WK = 1, WQ = 2, BK = 4, BQ = 8;
export const F_CAPTURE = 1, F_EP = 2, F_CASTLE = 4, F_DOUBLE = 8, F_PROMO = 16;

export interface Move { from: number; to: number; flags: number; promo: number; }

export interface Position {
  b: number[];          // 64 squares
  side: number;         // 1 white to move, -1 black
  castle: number;
  ep: number;           // en-passant target or -1
  half: number;         // half-move clock (50-move rule)
  full: number;
  seen: string[];       // position keys so far (threefold repetition)
}

export function sq(s: number): string { return "abcdefgh"[s & 7] + "12345678"[s >> 3]; }
export function moveText(m: Move): string { return sq(m.from) + sq(m.to) + (m.promo ? "nbrq"[Math.abs(m.promo) - 2] : ""); }

export function initial(): Position {
  const back = [ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP, KNIGHT, ROOK];
  const b = new Array(64).fill(0);
  for (let f = 0; f < 8; f++) { b[f] = back[f]; b[8 + f] = PAWN; b[48 + f] = -PAWN; b[56 + f] = -back[f]; }
  const p: Position = { b, side: 1, castle: WK | WQ | BK | BQ, ep: -1, half: 0, full: 1, seen: [] };
  p.seen.push(key(p));
  return p;
}

export function key(p: Position): string {
  return p.b.map((x) => ".PNBRQKpnbrqk"[x > 0 ? x : x < 0 ? 6 - x : 0]).join("") + (p.side === 1 ? "w" : "b") + p.castle + ":" + p.ep;
}

// ---------------------------------------------------------------- attacks
const KNIGHT_D = [17, 15, 10, 6, -6, -10, -15, -17], KING_D = [1, -1, 8, -8, 9, 7, -7, -9];
const DIAG_D = [9, 7, -7, -9], LINE_D = [1, -1, 8, -8];

function step(s: number, d: number): number {
  const t = s + d;
  if (t < 0 || t > 63) return -1;
  return Math.abs((t & 7) - (s & 7)) <= 2 ? t : -1;
}

export function attacked(p: Position, s0: number, by: number): boolean {
  const b = p.b;
  const pr = by === 1 ? -8 : 8;
  for (const df of [-1, 1]) {
    const f = (s0 & 7) + df, s = s0 + pr + df;
    if (f >= 0 && f < 8 && s >= 0 && s < 64 && b[s] === by * PAWN) return true;
  }
  for (const d of KNIGHT_D) { const t = step(s0, d); if (t >= 0 && b[t] === by * KNIGHT) return true; }
  for (const d of KING_D) { const t = step(s0, d); if (t >= 0 && b[t] === by * KING) return true; }
  for (const d of DIAG_D) for (let s = s0, t = step(s, d); t >= 0; s = t, t = step(s, d)) {
    if (b[t] === 0) continue;
    if (b[t] === by * BISHOP || b[t] === by * QUEEN) return true;
    break;
  }
  for (const d of LINE_D) for (let s = s0, t = step(s, d); t >= 0; s = t, t = step(s, d)) {
    if (Math.abs(d) === 1 && (t >> 3) !== (s >> 3)) break;
    if (b[t] === 0) continue;
    if (b[t] === by * ROOK || b[t] === by * QUEEN) return true;
    break;
  }
  return false;
}

export function kingSquare(p: Position, who: number): number { return p.b.indexOf(who * KING); }
export function inCheck(p: Position, who: number): boolean { const k = kingSquare(p, who); return k >= 0 && attacked(p, k, -who); }

// ---------------------------------------------------------------- generation
function pseudo(p: Position): Move[] {
  const ms: Move[] = [], b = p.b, me = p.side;
  const add = (s: number, t: number) => {
    if (b[t] * me > 0) return;
    ms.push({ from: s, to: t, flags: b[t] !== 0 ? F_CAPTURE : 0, promo: 0 });
  };
  for (let s = 0; s < 64; s++) {
    const pc = b[s] * me;
    if (pc <= 0) continue;
    if (pc === PAWN) {
      const dir = me * 8, start = me === 1 ? 1 : 6, last = me === 1 ? 7 : 0;
      const t = s + dir;
      if (t >= 0 && t < 64 && b[t] === 0) {
        if ((t >> 3) === last) promos(s, t, 0, me, ms);
        else {
          ms.push({ from: s, to: t, flags: 0, promo: 0 });
          const t2 = t + dir;
          if ((s >> 3) === start && b[t2] === 0) ms.push({ from: s, to: t2, flags: F_DOUBLE, promo: 0 });
        }
      }
      for (const df of [-1, 1]) {
        const f = (s & 7) + df; if (f < 0 || f > 7) continue;
        const c = s + dir + df; if (c < 0 || c > 63) continue;
        if (b[c] * me < 0) {
          if ((c >> 3) === last) promos(s, c, F_CAPTURE, me, ms);
          else ms.push({ from: s, to: c, flags: F_CAPTURE, promo: 0 });
        } else if (c === p.ep) ms.push({ from: s, to: c, flags: F_CAPTURE | F_EP, promo: 0 });
      }
    } else if (pc === KNIGHT) {
      for (const d of KNIGHT_D) { const t = step(s, d); if (t >= 0) add(s, t); }
    } else if (pc === KING) {
      for (const d of KING_D) { const t = step(s, d); if (t >= 0) add(s, t); }
      castles(p, s, ms);
    } else {
      const dirs = pc === BISHOP ? DIAG_D : pc === ROOK ? LINE_D : DIAG_D.concat(LINE_D);
      for (const d of dirs) for (let c = s, t = step(c, d); t >= 0; c = t, t = step(c, d)) {
        if (Math.abs(d) === 1 && (t >> 3) !== (c >> 3)) break;
        if (b[t] * me > 0) break;
        if (b[t] !== 0) { ms.push({ from: s, to: t, flags: F_CAPTURE, promo: 0 }); break; }
        ms.push({ from: s, to: t, flags: 0, promo: 0 });
      }
    }
  }
  return ms;
}

function promos(s: number, t: number, fl: number, me: number, ms: Move[]) {
  for (const pc of [QUEEN, KNIGHT, ROOK, BISHOP]) ms.push({ from: s, to: t, flags: fl | F_PROMO, promo: pc * me });
}

function castles(p: Position, s: number, ms: Move[]) {
  const me = p.side, b = p.b, home = me === 1 ? 4 : 60;
  if (s !== home || attacked(p, s, -me)) return;
  const kr = me === 1 ? WK : BK, qr = me === 1 ? WQ : BQ;
  if ((p.castle & kr) && b[s + 1] === 0 && b[s + 2] === 0 && b[s + 3] === me * ROOK && !attacked(p, s + 1, -me) && !attacked(p, s + 2, -me))
    ms.push({ from: s, to: s + 2, flags: F_CASTLE, promo: 0 });
  if ((p.castle & qr) && b[s - 1] === 0 && b[s - 2] === 0 && b[s - 3] === 0 && b[s - 4] === me * ROOK && !attacked(p, s - 1, -me) && !attacked(p, s - 2, -me))
    ms.push({ from: s, to: s - 2, flags: F_CASTLE, promo: 0 });
}

/** A new position with the move made (the input is not changed). */
export function make(p: Position, m: Move): Position {
  const b = p.b.slice(), me = p.side, pc = b[m.from];
  let captured = b[m.to];
  if (m.flags & F_EP) { const cap = m.to - me * 8; captured = b[cap]; b[cap] = 0; }
  b[m.to] = (m.flags & F_PROMO) ? m.promo : pc;
  b[m.from] = 0;
  if (m.flags & F_CASTLE) {
    if (m.to > m.from) { b[m.to - 1] = b[m.to + 1]; b[m.to + 1] = 0; }
    else { b[m.to + 1] = b[m.to - 2]; b[m.to - 2] = 0; }
  }
  let castle = p.castle;
  for (const s of [m.from, m.to]) {
    if (s === 4) castle &= ~(WK | WQ); if (s === 60) castle &= ~(BK | BQ);
    if (s === 0) castle &= ~WQ; if (s === 7) castle &= ~WK; if (s === 56) castle &= ~BQ; if (s === 63) castle &= ~BK;
  }
  const q: Position = {
    b, side: -me, castle, ep: (m.flags & F_DOUBLE) ? (m.from + m.to) / 2 : -1,
    half: (Math.abs(pc) === PAWN || captured !== 0) ? 0 : p.half + 1,
    full: me === -1 ? p.full + 1 : p.full, seen: p.seen.slice(),
  };
  q.seen.push(key(q));
  return q;
}

export function legalMoves(p: Position): Move[] {
  return pseudo(p).filter((m) => !inCheck(make(p, m), p.side));
}

export type Result = "playing" | "white_won" | "black_won" | "draw";
export function status(p: Position): { result: Result; reason: string } {
  if (legalMoves(p).length === 0)
    return inCheck(p, p.side) ? { result: p.side === 1 ? "black_won" : "white_won", reason: "checkmate" } : { result: "draw", reason: "stalemate" };
  if (p.half >= 100) return { result: "draw", reason: "fifty_moves" };
  const k = p.seen[p.seen.length - 1];
  if (p.seen.filter((x) => x === k).length >= 3) return { result: "draw", reason: "repetition" };
  let minors = 0, others = 0;
  for (const x of p.b) { const a = Math.abs(x); if (a === KNIGHT || a === BISHOP) minors++; else if (a !== 0 && a !== KING) others++; }
  if (others === 0 && minors <= 1) return { result: "draw", reason: "insufficient_material" };
  return { result: "playing", reason: "" };
}

/** Validate a stored position from the database before trusting it (defence in depth against a corrupted row). */
export function isPosition(x: unknown): x is Position {
  const p = x as Position;
  return !!p && Array.isArray(p.b) && p.b.length === 64 && p.b.every((v) => Number.isInteger(v) && v >= -6 && v <= 6)
    && (p.side === 1 || p.side === -1) && Number.isInteger(p.castle) && p.castle >= 0 && p.castle <= 15
    && Number.isInteger(p.ep) && p.ep >= -1 && p.ep <= 63 && Number.isInteger(p.half) && Number.isInteger(p.full)
    && Array.isArray(p.seen) && p.seen.every((s) => typeof s === "string");
}
