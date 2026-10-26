# Queen clips (exec'd after anims.py). The crowned queen with her orb staff (sheet "クイーン | 全モーション詳細（決定版）").
# The weapon bone runs up the staff. She never strikes: she glides in, chants and sweeps the board with light.
# The light itself - circles, pillars, spears, bursts - is drawn by the viewers on the frames named below.
STAFF_REST = ("weapon", (0.12, -0.25, 0.96), (0, -1, 0))   # staff upright before her right side

QUEEN_DUEL = 1.3   # the queen fights a pawn from 1.3 squares (viewer / PawnBattle reach 0.3)
T_Q_GUARD = (T_GUARD[0], T_GUARD[1] - (QUEEN_DUEL - PAWN_DUEL), T_GUARD[2] + 0.07)   # top of the X: the orb stays clear of the body
T_Q_KILL = (0.0, -QUEEN_DUEL + 0.04, 0.72)   # the front of the pawn's chest (the orb goes in)
Q_ORB = (0.95 + 0.1) * 0.85   # board units from the bone head to the orb
QUEEN_BLOCK_LUNGE = 0.0087   # solved: the orb meets the pawn's blades on frame 16, 3.7 cm clear of its body
# (clip, frame) -> root lunge (authoring units), solved so the orb lands on its target
QN_LUNGE = {('Combo', 8): 0.1271, ('Combo', 13): 0.0769, ('Combo', 18): 0.1423, ('Combo', 23): 0.1271, ('Combo', 28): 0.077, ('Combo', 34): 0.1271, ('Combo', 40): 0.0769, ('Combo', 46): 0.0771, ('Combo', 52): 0.0771, ('Combo', 58): 0.1271, ('Attack', 16): 0.0304}
# the light skills (frames the viewers time their effects on)
Q_CHANT_CIRCLE, Q_CHANT_END = 26, 58
Q_SKILL_PILLARS, Q_SKILL_BURST = 40, 60      # 光の裁き: pillars fall, the burst engulfs the pawn (who survives on its guard)
Q_ULT_SPEARS, Q_ULT_PIERCE = 40, 46          # 女王の審判: the spears rain, one pierces the pawn (kill)

def queen_clips(rig):
    G = P(ARMS(upper_arm_R=(-0.3, -0.3, -0.9), forearm_R=(0.1, -0.85, 0.5),
               upper_arm_L=(0.3, -0.05, -0.95), forearm_L=(0.25, -0.5, -0.83)),
          spine=(2, 0, 0), head=(-4, 0, 0))
    out = []
    hold = (STAFF_REST,)
    ql = lambda name, f, d=-0.05: QN_LUNGE.get((name, f), d)
    lift = P(G, ARMS(upper_arm_R=(-0.3, -0.25, 0.3), forearm_R=(0.05, -0.2, 0.98)), spine=(-4, 0, 0), head=(-10, 0, 0))
    sky = [("weapon", (0.05, -0.1, 1), (0, -1, 0))]
    palm = ARMS(upper_arm_L=(0.75, -0.3, -0.3), forearm_L=(0.75, -0.4, 0.3))   # free hand opened outward
    # ---- Idle (8): 静かに立つ / 杖を掲げる / 魔力を纏う / マントが揺れる / 周囲に光の粒 / 優雅に回転 / 姿勢を整える / 待機完了
    out.append(clip(rig, "Idle", [
        K(1, G), K(12, lift, aims=sky), K(24, P(lift, palm), aims=sky), K(36, add(G, P(spine=(0, 0, 4), chest=(-2, 0, 0)))),
        K(48, P(G, palm, head=(0, 12, 0))), K(60, G, None, (0, 0, 40)), K(72, G, None, (0, 0, 0)), K(84, add(G, P(head=(-4, 0, 0)))),
        K(96, G)], loop=True, aims=hold, flowing=True))
    # ---- Walk (sheet "移動"): a gliding stately step; the gown hides the legs, the body barely bobs
    def step(s):
        return P(G, {"thigh.L": (14 * s, 0, 2), "shin.L": (-8 if s > 0 else -18, 0, 0), "foot.L": (6 * s, 0, 0)},
                 {"thigh.R": (-14 * s, 0, -2), "shin.R": (-18 if s > 0 else -8, 0, 0), "foot.R": (-6 * s, 0, 0)},
                 chest=(0, -4 * s, 0), hips=(0, 5 * s, 0))
    def passing(lift_):
        o = "R" if lift_ == "L" else "L"
        return P(G, {f"thigh.{lift_}": (22, 0, 0), f"shin.{lift_}": (-36, 0, 0), f"thigh.{o}": (2, 0, 0), f"shin.{o}": (-6, 0, 0)})
    out.append(clip(rig, "Walk", [K(1, step(1)), K(13, passing("R")), K(25, step(-1)), K(37, passing("L")), K(49, step(1))],
                    loop=True, aims=hold))
    # ---- Chant (sheet "抜刀・詠唱" 10): 杖に触れる / 魔力が集まる / 宝石が発光 / 詠唱開始 / 天空に掲げる / 魔法陣展開 / 力が増幅
    #      / 光が降り注ぐ / マントが舞う / 詠唱完了
    touch = P(G, ARMS(upper_arm_L=(0.05, -0.5, -0.86), forearm_L=(-0.6, -0.75, 0.25)), head=(6, 0, 0))   # left hand to the staff
    gather = P(G, ARMS(upper_arm_R=(-0.3, -0.5, -0.8), forearm_R=(0.3, -0.9, 0.3)), palm, spine=(4, 0, 0), head=(8, 0, 0))
    raised = P(G, ARMS(upper_arm_R=(-0.2, -0.15, 0.97), forearm_R=(0.05, -0.1, 0.99)), palm, spine=(-8, 0, 0), chest=(-6, 0, 0), head=(-18, 0, 0))
    out.append(clip(rig, "Chant", [
        K(1, G), K(6, touch), K(12, gather, aims=[("weapon", (0.3, -0.6, 0.74), (0, -1, 0))]),
        K(18, add(gather, P(head=(-4, 0, 0)))), K(22, lift, aims=sky), K(Q_CHANT_CIRCLE, raised, aims=sky),
        K(36, add(raised, P(spine=(-4, 0, 3))), aims=sky), K(44, add(raised, P(spine=(-2, 0, -3))), aims=sky),
        K(50, raised, None, (0, 0, 30), aims=sky), K(Q_CHANT_END, G, None, (0, 0, 0))], aims=hold, flowing=True))

    # (no melee: user "クイーンに戦闘モーションはいらない / 派手な魔法で一掃してほしい" - she only casts)
    # ---- Skill 光の裁き (12): 詠唱開始 / 大きな魔法陣 / 天空に光が集まる / 無数の光の刃 / 光の柱が降下 / 地面に魔法陣
    #      / 光の刃が拡散 / 周囲に連鎖 / 敵を包み込む / 最大出力の爆発 / 余波が広がる / 収束し静寂へ
    point = P(G, ARMS(upper_arm_R=(-0.15, -0.95, 0.25), forearm_R=(0.0, -0.95, 0.3)), palm, spine=(8, 0, 0), head=(-10, 0, 0))
    toward = [("weapon", (0, -1, 0.35), (0, 0, 1))]
    out.append(clip(rig, "Skill", [
        K(1, G), K(8, gather), K(16, raised, aims=sky), K(28, add(raised, P(spine=(-4, 0, 0))), aims=sky),
        K(Q_SKILL_PILLARS - 4, raised, aims=sky), K(Q_SKILL_PILLARS, point, aims=toward), K(50, point, aims=toward),
        K(Q_SKILL_BURST, add(point, P(spine=(-8, 0, 0))), (0, 0.04, 0), aims=toward), K(70, G), K(78, G)], aims=hold, flowing=True))
    # ---- Ultimate 女王の審判 (10): 世界が静止 / 宇宙のような魔法陣 / 無数の光の結晶 / 天空の扉が開く / 光の軍勢召喚
    #      / 光の槍が降り注ぐ / 敵を貫く / 大地が浄化される / 圧倒的な光の爆発 / 女王の立つ姿
    both = P(raised, ARMS(upper_arm_L=(0.3, -0.1, 0.95), forearm_L=(0.1, -0.1, 0.99)))
    out.append(clip(rig, "Ultimate", [
        K(1, G), K(6, add(G, P(head=(-6, 0, 0)))), K(14, raised, aims=sky), K(24, both, aims=sky), K(32, add(both, P(spine=(-6, 0, 0))), aims=sky),
        K(Q_ULT_SPEARS, point, aims=toward), K(Q_ULT_PIERCE, add(point, P(spine=(6, 0, 0))), aims=toward),
        K(56, add(point, P(spine=(-10, 0, 0))), aims=toward), K(64, lift, aims=sky), K(76, G)], aims=hold, flowing=True))

    # ---- Block: the staff held across as a ward
    parry = P(ARMS(upper_arm_R=(-0.35, -0.6, 0.0), forearm_R=(0.35, -0.6, 0.7), upper_arm_L=(0.35, -0.6, 0.0), forearm_L=(-0.35, -0.6, 0.7)),
              {"thigh.L": (16, 0, 2), "shin.L": (-22, 0, 0), "thigh.R": (-8, 0, -2), "shin.R": (-16, 0, 0), "foot.R": (16, 0, 0)},
              spine=(4, 0, 0), head=(-6, 0, 0))
    across = [("weapon", (0.95, -0.2, 0.25), (0, -1, 0))]
    out.append(clip(rig, "Block", [K(1, G), K(9, parry, aims=across), K(16, parry, aims=across),
                                   K(18, add(parry, P(spine=(-8, 0, 0))), (0, 0.05, 0), aims=across), K(26, parry, (0, 0.04, 0), aims=across),
                                   K(36, G)], aims=hold, flowing=True))
    # ---- Hit (sheet "被弾" 6): 被弾 / よろめく / ひざをつく / マントが崩れる / 回復へ / 立ち上がる
    reel = add(parry, P(spine=(-20, 0, 6), head=(-18, 10, 0), thigh_L=(-10, 0, 0), thigh_R=(12, 0, 0), shin_R=(-26, 0, 0)))
    knee = P({"thigh.L": (70, 0, 8), "shin.L": (-110, 0, 0), "foot.L": (30, 0, 0), "thigh.R": (10, 0, -8), "shin.R": (-120, 0, 0), "foot.R": (50, 0, 0)},
             ARMS(upper_arm_R=(-0.3, -0.4, -0.86), forearm_R=(0.1, -0.6, 0.79)), spine=(24, 0, 0), head=(6, 0, 0))
    out.append(clip(rig, "Hit", [K(1, G), K(9, parry, aims=across), K(16, parry, aims=across),
                                 K(19, reel, (0, 0.11, 0), (-5, 0, 2), aims=across), K(28, knee, (0, 0.12, 0), aims=[STAFF_REST]),
                                 K(36, knee, (0, 0.12, 0), aims=[STAFF_REST]), K(46, add(G, P(spine=(10, 0, 0))), (0, 0.1, 0)),
                                 K(56, G, (0, 0.06, 0))], aims=hold, flowing=True))
    # ---- Death (sheet "死亡" 6): 致命傷 / 膝から崩れる / 杖を落とす / 倒れ込む / 光が消える / 静寂
    kneel = P({"thigh.L": (85, 0, 6), "shin.L": (-120, 0, 0), "foot.L": (30, 0, 0), "thigh.R": (20, 0, -6), "shin.R": (-125, 0, 0), "foot.R": (50, 0, 0)},
              ARMS(upper_arm_R=(-0.2, -0.2, -0.95), forearm_R=(-0.1, -0.5, -0.85), upper_arm_L=(0.2, -0.2, -0.95), forearm_L=(0.1, -0.5, -0.85)),
              spine=(24, 0, -6), chest=(10, 0, 0), head=(26, -15, 0))
    flat = P({"thigh.L": (10, 0, 6), "shin.L": (-20, 0, 0), "thigh.R": (6, 0, -6), "shin.R": (-14, 0, 0)},
             ARMS(upper_arm_R=(-0.3, -0.25, 0.92), forearm_R=(-0.2, -0.45, 0.87), upper_arm_L=(0.3, -0.25, 0.92), forearm_L=(0.2, -0.45, 0.87)),
             spine=(4, 0, 0), head=(-30, 30, 0))
    free = [("weapon", None, None)]
    out.append(clip(rig, "Death", [
        K(1, G), K(9, parry, aims=across), K(14, parry, aims=across), K(17, reel, (0, 0.08, 0), (-6, 0, 3), aims=free),
        K(28, kneel, (0, 0.04, 0), drop=0.52, aims=free), K(34, kneel, (0, 0, 0), (8, 0, 0), 0.52, free),
        K(46, flat, (0, -0.16, 0.02), (82, 0, 0), 0.1, free), K(50, flat, (0, -0.17, 0.035), (78, 0, 0), 0.1, free),
        K(56, flat, (0, -0.17, 0.02), (82, 0, 0), 0.1, free), K(74, flat, (0, -0.17, 0.02), (82, 0, 0), 0.1, free)], aims=hold))
    # ---- Victory (sheet "勝利" 6): 敵を見下ろす / 杖を掲げる / 光が集まる / 優雅に回転 / マントが舞う / 勝利の立ち姿
    out.append(clip(rig, "Victory", [K(1, G), K(8, P(G, head=(14, 0, 0))), K(16, raised, aims=sky), K(26, P(raised), aims=sky),
                                     K(36, raised, None, (0, 0, 180), aims=sky), K(46, P(lift, palm), None, (0, 0, 360), aims=sky),
                                     K(58, G, None, (0, 0, 360))], aims=hold, flowing=True))
    for a in out: natural_wrist(rig, a, "hand.R", tip=Q_ORB)   # the fist turns with the staff; the orb stays where it was solved to land
    return out

CLIPS["Queen"] = queen_clips
