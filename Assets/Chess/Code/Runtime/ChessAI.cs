using System.Collections.Generic;
using System.Diagnostics;

// The CPU player: iterative-deepening negamax with alpha-beta, captures-first ordering and a quiescence search,
// scored by material + piece-square tables. Pure C#: it runs on a worker thread against a copy of the position.
public static class ChessAI
{
    static readonly int[] Value = { 0, 100, 320, 330, 500, 900, 0 };

    // piece-square tables from white's side, a8 first (rank 8 row first) - the usual "simplified" tables
    static readonly int[][] Pst =
    {
        null,
        new[] { 0,0,0,0,0,0,0,0, 50,50,50,50,50,50,50,50, 10,10,20,30,30,20,10,10, 5,5,10,25,25,10,5,5,
                0,0,0,20,20,0,0,0, 5,-5,-10,0,0,-10,-5,5, 5,10,10,-20,-20,10,10,5, 0,0,0,0,0,0,0,0 },
        new[] { -50,-40,-30,-30,-30,-30,-40,-50, -40,-20,0,0,0,0,-20,-40, -30,0,10,15,15,10,0,-30, -30,5,15,20,20,15,5,-30,
                -30,0,15,20,20,15,0,-30, -30,5,10,15,15,10,5,-30, -40,-20,0,5,5,0,-20,-40, -50,-40,-30,-30,-30,-30,-40,-50 },
        new[] { -20,-10,-10,-10,-10,-10,-10,-20, -10,0,0,0,0,0,0,-10, -10,0,5,10,10,5,0,-10, -10,5,5,10,10,5,5,-10,
                -10,0,10,10,10,10,0,-10, -10,10,10,10,10,10,10,-10, -10,5,0,0,0,0,5,-10, -20,-10,-10,-10,-10,-10,-10,-20 },
        new[] { 0,0,0,0,0,0,0,0, 5,10,10,10,10,10,10,5, -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5,
                -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5, 0,0,0,5,5,0,0,0 },
        new[] { -20,-10,-10,-5,-5,-10,-10,-20, -10,0,0,0,0,0,0,-10, -10,0,5,5,5,5,0,-10, -5,0,5,5,5,5,0,-5,
                0,0,5,5,5,5,0,-5, -10,5,5,5,5,5,0,-10, -10,0,5,0,0,0,0,-10, -20,-10,-10,-5,-5,-10,-10,-20 },
        new[] { -30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30,
                -20,-30,-30,-40,-40,-30,-30,-20, -10,-20,-20,-20,-20,-20,-20,-10, 20,20,0,0,0,0,20,20, 20,30,10,0,0,10,30,20 },
    };

    // score from the side to move's view
    public static int Evaluate(ChessRules r)
    {
        int score = 0;
        for (int s = 0; s < 64; s++)
        {
            int p = r.b[s]; if (p == 0) continue;
            int a = p > 0 ? p : -p;
            int idx = p > 0 ? (7 - ChessRules.Rank(s)) * 8 + ChessRules.File(s) : ChessRules.Rank(s) * 8 + ChessRules.File(s);
            int v = Value[a] + Pst[a][idx];
            score += p > 0 ? v : -v;
        }
        return score * r.side;
    }

    const int Mate = 100000;
    static Stopwatch clock;
    static long budgetMs;
    static bool stop;
    static int nodes;

    /// <summary>Best move within timeMs (and maxDepth plies). Slightly randomised among equal moves so games differ.</summary>
    public static ChessRules.Move Think(ChessRules root, int timeMs, int maxDepth, System.Random rng)
    {
        var r = root.Clone();
        var moves = r.Legal();
        if (moves.Count == 0) return default;
        // shuffle, then the search's stable ordering keeps ties random
        for (int i = moves.Count - 1; i > 0; i--) { int j = rng.Next(i + 1); (moves[i], moves[j]) = (moves[j], moves[i]); }
        clock = Stopwatch.StartNew(); budgetMs = timeMs; stop = false; nodes = 0;
        var best = moves[0];
        for (int depth = 1; depth <= maxDepth; depth++)
        {
            int alpha = -Mate - 1, bestScore = -Mate - 1;
            ChessRules.Move bestHere = moves[0];
            Order(r, moves, best);
            foreach (var m in moves)
            {
                r.Make(m);
                int sc = -Search(r, depth - 1, -Mate - 1, -alpha, 1);
                r.Unmake();
                if (stop) break;
                if (sc > bestScore) { bestScore = sc; bestHere = m; }
                if (sc > alpha) alpha = sc;
            }
            if (stop) break;           // keep the last fully searched depth's choice
            best = bestHere;
            if (bestScore >= Mate - 100) break;   // a forced mate found
        }
        return best;
    }

    static int Search(ChessRules r, int depth, int alpha, int beta, int ply)
    {
        if ((++nodes & 1023) == 0 && clock.ElapsedMilliseconds > budgetMs) stop = true;
        if (stop) return 0;
        if (depth <= 0) return Quiesce(r, alpha, beta, 0);
        var moves = r.Pseudo();
        Order(r, moves, default);
        int me = r.side, legal = 0;
        foreach (var m in moves)
        {
            r.Make(m);
            if (r.InCheck(me)) { r.Unmake(); continue; }
            legal++;
            int sc = -Search(r, depth - 1, -beta, -alpha, ply + 1);
            r.Unmake();
            if (stop) return 0;
            if (sc >= beta) return beta;
            if (sc > alpha) alpha = sc;
        }
        if (legal == 0) return r.InCheck(me) ? -Mate + ply : 0;
        if (r.halfmove >= 100) return 0;
        return alpha;
    }

    static int Quiesce(ChessRules r, int alpha, int beta, int qdepth)
    {
        int stand = Evaluate(r);
        if (stand >= beta) return beta;
        if (stand > alpha) alpha = stand;
        if (qdepth > 6) return alpha;
        var moves = r.Pseudo(true);
        Order(r, moves, default);
        int me = r.side;
        foreach (var m in moves)
        {
            r.Make(m);
            if (r.InCheck(me)) { r.Unmake(); continue; }
            int sc = -Quiesce(r, -beta, -alpha, qdepth + 1);
            r.Unmake();
            if (sc >= beta) return beta;
            if (sc > alpha) alpha = sc;
        }
        return alpha;
    }

    // the previous best first, then captures by most valuable victim / least valuable attacker, promotions
    static void Order(ChessRules r, List<ChessRules.Move> ms, ChessRules.Move first)
    {
        int Score(ChessRules.Move m)
        {
            if (m.from == first.from && m.to == first.to && m.promo == first.promo && (first.from | first.to) != 0) return 1000000;
            int s = 0;
            if (m.Is(ChessRules.Flag.Capture))
            {
                int victim = m.Is(ChessRules.Flag.EnPassant) ? 1 : System.Math.Abs((int)r.b[m.to]);
                s += 10000 + Value[victim] * 10 - Value[System.Math.Abs((int)r.b[m.from])] / 10;
            }
            if (m.Is(ChessRules.Flag.Promo)) s += 9000 + System.Math.Abs((int)m.promo);
            return s;
        }
        var keyed = new List<(int, int, ChessRules.Move)>(ms.Count);
        for (int i = 0; i < ms.Count; i++) keyed.Add((-Score(ms[i]), i, ms[i]));
        keyed.Sort((a, b) => a.Item1 != b.Item1 ? a.Item1.CompareTo(b.Item1) : a.Item2.CompareTo(b.Item2));
        for (int i = 0; i < ms.Count; i++) ms[i] = keyed[i].Item3;
    }
}
