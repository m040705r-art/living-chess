using System.Collections.Generic;

// The rules of chess, independent of Unity (the CPU searches copies of it on a worker thread).
// Squares are 0..63 = rank * 8 + file (a1 = 0, h1 = 7, a8 = 56). Pieces: 1 pawn, 2 knight, 3 bishop, 4 rook,
// 5 queen, 6 king; white positive, black negative, 0 empty.
public class ChessRules
{
    public const int Pawn = 1, Knight = 2, Bishop = 3, Rook = 4, Queen = 5, King = 6;
    public const int WK = 1, WQ = 2, BK = 4, BQ = 8;   // castling rights
    [System.Flags] public enum Flag : byte { None = 0, Capture = 1, EnPassant = 2, Castle = 4, Double = 8, Promo = 16 }

    public struct Move
    {
        public byte from, to; public sbyte promo; public Flag flags;
        public Move(int f, int t, Flag fl = Flag.None, int pr = 0) { from = (byte)f; to = (byte)t; flags = fl; promo = (sbyte)pr; }
        public bool Is(Flag f) => (flags & f) != 0;
        public override string ToString() => Sq(from) + Sq(to) + (promo != 0 ? "nbrq"[System.Math.Abs(promo) - 2].ToString() : "");
    }

    struct Undo { public Move m; public sbyte captured; public int castle, ep, half; }

    public sbyte[] b = new sbyte[64];
    public int side = 1;            // 1 white to move, -1 black
    public int castle = WK | WQ | BK | BQ;
    public int ep = -1;             // en-passant target square, or -1
    public int halfmove, fullmove = 1;
    readonly Stack<Undo> undo = new Stack<Undo>();
    readonly List<ulong> history = new List<ulong>();   // position keys, for threefold repetition

    public static string Sq(int s) => "" + (char)('a' + s % 8) + (char)('1' + s / 8);
    public static int File(int s) => s & 7;
    public static int Rank(int s) => s >> 3;

    public ChessRules() { Reset(); }

    public void Reset()
    {
        sbyte[] back = { Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook };
        System.Array.Clear(b, 0, 64);
        for (int f = 0; f < 8; f++)
        {
            b[f] = back[f]; b[8 + f] = Pawn;
            b[48 + f] = -Pawn; b[56 + f] = (sbyte)-back[f];
        }
        side = 1; castle = WK | WQ | BK | BQ; ep = -1; halfmove = 0; fullmove = 1;
        undo.Clear(); history.Clear(); history.Add(Key());
    }

    public ChessRules Clone()
    {
        var c = new ChessRules();
        System.Array.Copy(b, c.b, 64);
        c.side = side; c.castle = castle; c.ep = ep; c.halfmove = halfmove; c.fullmove = fullmove;
        c.history.Clear(); c.history.AddRange(history);
        return c;
    }

    // ---------------------------------------------------------------- attacks
    static readonly int[] KnightD = { 17, 15, 10, 6, -6, -10, -15, -17 };
    static readonly int[] KingD = { 1, -1, 8, -8, 9, 7, -7, -9 };
    static readonly int[] DiagD = { 9, 7, -7, -9 }, LineD = { 1, -1, 8, -8 };

    // a step from s by d stays on the board (no wrapping round the a/h files)
    static bool Step(int s, int d, out int t)
    {
        t = s + d;
        if (t < 0 || t > 63) return false;
        return System.Math.Abs(File(t) - File(s)) <= 2;
    }

    public bool Attacked(int sq, int by)
    {
        // pawns
        int pr = by == 1 ? -8 : 8;
        foreach (int df in new[] { -1, 1 })
        {
            int f = File(sq) + df, s = sq + pr + df;
            if (f >= 0 && f < 8 && s >= 0 && s < 64 && b[s] == by * Pawn) return true;
        }
        foreach (int d in KnightD) if (Step(sq, d, out int t) && b[t] == by * Knight) return true;
        foreach (int d in KingD) if (Step(sq, d, out int t) && b[t] == by * King) return true;
        foreach (int d in DiagD) for (int s = sq; Step(s, d, out int t); s = t)
        {
            if (b[t] == 0) continue;
            if (b[t] == by * Bishop || b[t] == by * Queen) return true;
            break;
        }
        foreach (int d in LineD) for (int s = sq; Step(s, d, out int t); s = t)
        {
            if (System.Math.Abs(d) == 1 && Rank(t) != Rank(s)) break;
            if (b[t] == 0) continue;
            if (b[t] == by * Rook || b[t] == by * Queen) return true;
            break;
        }
        return false;
    }

    public int KingSquare(int who) { for (int s = 0; s < 64; s++) if (b[s] == who * King) return s; return -1; }
    public bool InCheck(int who) { int k = KingSquare(who); return k >= 0 && Attacked(k, -who); }

    // ---------------------------------------------------------------- move generation
    public List<Move> Pseudo(bool capturesOnly = false)
    {
        var ms = new List<Move>(48);
        int me = side;
        for (int s = 0; s < 64; s++)
        {
            int p = b[s] * me;
            if (p <= 0) continue;
            switch (p)
            {
                case Pawn: PawnMoves(s, ms, capturesOnly); break;
                case Knight: foreach (int d in KnightD) if (Step(s, d, out int t)) Add(s, t, ms, capturesOnly); break;
                case King:
                    foreach (int d in KingD) if (Step(s, d, out int t)) Add(s, t, ms, capturesOnly);
                    if (!capturesOnly) Castles(s, ms);
                    break;
                default:
                    if (p == Bishop || p == Queen) foreach (int d in DiagD) Slide(s, d, ms, capturesOnly);
                    if (p == Rook || p == Queen) foreach (int d in LineD) Slide(s, d, ms, capturesOnly);
                    break;
            }
        }
        return ms;
    }

    void Add(int s, int t, List<Move> ms, bool capturesOnly)
    {
        if (b[t] * side > 0) return;
        if (b[t] != 0) ms.Add(new Move(s, t, Flag.Capture));
        else if (!capturesOnly) ms.Add(new Move(s, t));
    }

    void Slide(int s, int d, List<Move> ms, bool capturesOnly)
    {
        for (int c = s; Step(c, d, out int t); c = t)
        {
            if (System.Math.Abs(d) == 1 && Rank(t) != Rank(c)) break;
            if (b[t] * side > 0) break;
            if (b[t] != 0) { ms.Add(new Move(s, t, Flag.Capture)); break; }
            if (!capturesOnly) ms.Add(new Move(s, t));
        }
    }

    void PawnMoves(int s, List<Move> ms, bool capturesOnly)
    {
        int dir = side * 8, start = side == 1 ? 1 : 6, last = side == 1 ? 7 : 0;
        int t = s + dir;
        if (t >= 0 && t < 64 && b[t] == 0)
        {
            if (Rank(t) == last) Promos(s, t, Flag.None, ms);
            else if (!capturesOnly)
            {
                ms.Add(new Move(s, t));
                int t2 = t + dir;
                if (Rank(s) == start && b[t2] == 0) ms.Add(new Move(s, t2, Flag.Double));
            }
        }
        foreach (int df in new[] { -1, 1 })
        {
            int f = File(s) + df; if (f < 0 || f > 7) continue;
            int c = s + dir + df; if (c < 0 || c > 63) continue;
            if (b[c] * side < 0)
            {
                if (Rank(c) == last) Promos(s, c, Flag.Capture, ms);
                else ms.Add(new Move(s, c, Flag.Capture));
            }
            else if (c == ep) ms.Add(new Move(s, c, Flag.Capture | Flag.EnPassant));
        }
    }

    void Promos(int s, int t, Flag fl, List<Move> ms)
    {
        foreach (int p in new[] { Queen, Knight, Rook, Bishop }) ms.Add(new Move(s, t, fl | Flag.Promo, p * side));
    }

    void Castles(int s, List<Move> ms)
    {
        int home = side == 1 ? 4 : 60;
        if (s != home || Attacked(s, -side)) return;
        int kr = side == 1 ? WK : BK, qr = side == 1 ? WQ : BQ;
        if ((castle & kr) != 0 && b[s + 1] == 0 && b[s + 2] == 0 && b[s + 3] == side * Rook
            && !Attacked(s + 1, -side) && !Attacked(s + 2, -side))
            ms.Add(new Move(s, s + 2, Flag.Castle));
        if ((castle & qr) != 0 && b[s - 1] == 0 && b[s - 2] == 0 && b[s - 3] == 0 && b[s - 4] == side * Rook
            && !Attacked(s - 1, -side) && !Attacked(s - 2, -side))
            ms.Add(new Move(s, s - 2, Flag.Castle));
    }

    public List<Move> Legal()
    {
        var ms = Pseudo();
        var legal = new List<Move>(ms.Count);
        int me = side;
        foreach (var m in ms) { Make(m); if (!InCheck(me)) legal.Add(m); Unmake(); }
        return legal;
    }

    // ---------------------------------------------------------------- make / unmake
    public void Make(Move m)
    {
        var u = new Undo { m = m, castle = castle, ep = ep, half = halfmove, captured = b[m.to] };
        int p = b[m.from];
        if (m.Is(Flag.EnPassant)) { int cap = m.to - side * 8; u.captured = b[cap]; b[cap] = 0; }
        b[m.to] = m.Is(Flag.Promo) ? m.promo : (sbyte)p;
        b[m.from] = 0;
        if (m.Is(Flag.Castle))
        {
            if (m.to > m.from) { b[m.to - 1] = b[m.to + 1]; b[m.to + 1] = 0; }
            else { b[m.to + 1] = b[m.to - 2]; b[m.to - 2] = 0; }
        }
        // castling rights fall when a king or rook moves or a rook is taken on its corner
        foreach (int s in new[] { (int)m.from, m.to })
        {
            if (s == 4) castle &= ~(WK | WQ); if (s == 60) castle &= ~(BK | BQ);
            if (s == 0) castle &= ~WQ; if (s == 7) castle &= ~WK; if (s == 56) castle &= ~BQ; if (s == 63) castle &= ~BK;
        }
        ep = m.Is(Flag.Double) ? (m.from + m.to) / 2 : -1;
        halfmove = (System.Math.Abs(p) == Pawn || u.captured != 0) ? 0 : halfmove + 1;
        if (side == -1) fullmove++;
        side = -side;
        undo.Push(u);
        history.Add(Key());
    }

    public void Unmake()
    {
        var u = undo.Pop();
        history.RemoveAt(history.Count - 1);
        var m = u.m;
        side = -side;
        if (side == -1) fullmove--;
        int p = m.Is(Flag.Promo) ? side * Pawn : b[m.to];
        b[m.from] = (sbyte)p;
        if (m.Is(Flag.EnPassant)) { b[m.to] = 0; b[m.to - side * 8] = u.captured; }
        else b[m.to] = u.captured;
        if (m.Is(Flag.Castle))
        {
            if (m.to > m.from) { b[m.to + 1] = b[m.to - 1]; b[m.to - 1] = 0; }
            else { b[m.to - 2] = b[m.to + 1]; b[m.to + 1] = 0; }
        }
        castle = u.castle; ep = u.ep; halfmove = u.half;
    }

    // ---------------------------------------------------------------- end of game
    public enum Result { Playing, WhiteMates, BlackMates, Stalemate, FiftyMoves, Repetition, NoMaterial }

    public Result Status()
    {
        if (Legal().Count == 0) return InCheck(side) ? (side == 1 ? Result.BlackMates : Result.WhiteMates) : Result.Stalemate;
        if (halfmove >= 100) return Result.FiftyMoves;
        ulong k = history[history.Count - 1]; int seen = 0;
        foreach (var h in history) if (h == k) seen++;
        if (seen >= 3) return Result.Repetition;
        int minors = 0, others = 0;
        foreach (var x in b)
        {
            int a = System.Math.Abs(x);
            if (a == Knight || a == Bishop) minors++;
            else if (a != 0 && a != King) others++;
        }
        if (others == 0 && minors <= 1) return Result.NoMaterial;
        return Result.Playing;
    }

    // position key (Zobrist-like, deterministic tables)
    static readonly ulong[,] Z = MakeZ();
    static ulong[,] MakeZ()
    {
        var z = new ulong[13 * 64 + 1 + 16 + 64, 1];
        ulong x = 0x9E3779B97F4A7C15UL;
        for (int i = 0; i < z.GetLength(0); i++) { x ^= x << 13; x ^= x >> 7; x ^= x << 17; z[i, 0] = x; }
        return z;
    }
    public ulong Key()
    {
        ulong k = side == 1 ? Z[13 * 64, 0] : 0;
        for (int s = 0; s < 64; s++) if (b[s] != 0) k ^= Z[(b[s] + 6) * 64 + s, 0];
        k ^= Z[13 * 64 + 1 + castle, 0];
        if (ep >= 0) k ^= Z[13 * 64 + 17 + ep, 0];
        return k;
    }
}
