# Rook clips (exec'd after anims.py). The tower-helmed knight (rook.py) with sword and kite shield. It breaks into a
# run from where it stands (Charge, carried by the viewer / game) and slams into the target behind its shield on
# frame 16 of Attack (user: "攻撃するとき初めからダッシュしてタックル"), ploughing on through.
ROOK_TACKLE_FROM = 1.6   # squares between the rook and its target when the tackle starts
ROOK_RUN_FRAMES = 16   # the Attack's run-in covers |ROOK_LUNGE| in its first 16 frames: the Charge loop matches that pace
ROOK_LUNGE = -0.5   # authoring units: solved so the shield is IN CONTACT with the bracing pawn on frame 16 (BVH gap ~0)

ROOK_IAI_END = (0.75, -2.3)   # board units: where the Iai run ends (to the rook's left, so the pawn passes on its sword side)
# and forward - committed by the viewer. The cut lands while the pawn is still diagonally AHEAD: cutting level with it
# pointed the blade back toward the elbow, which read as a reverse grip (user: "逆手に持ってるように見える").
T_IAI = (0.0, -ROOK_TACKLE_FROM, 0.68)   # the target's chest as the rook passes it on IAI_HIT
IAI_HIT = 60   # the blade goes through on this frame of Iai
IAI_CUT_Y = 0.75   # board units the rook has advanced at IAI_HIT (the pawn is ROOK_TACKLE_FROM ahead)

R_SHIELD = ("shield", "strap", (0.3, -1, 0))
R_SWORD = ("weapon", (-0.15, -0.55, -0.82), (1, 0, 0))   # held low at the right side, point forward and down

def rook_clips(rig):
    STAND = P({"thigh.L": (10, 0, 4), "shin.L": (-14, 0, 0), "foot.L": (4, 0, 0), "thigh.R": (-4, 0, -4), "shin.R": (-10, 0, 0), "foot.R": (12, 0, 0)})
    GUARD = P(STAND, ARMS(upper_arm_L=(0.35, -0.35, -0.87), forearm_L=(-0.8, -0.5, 0.2),     # forearm across: shield faces front
                          upper_arm_R=(-0.25, -0.1, -0.96), forearm_R=(-0.1, -0.75, -0.6)),   # sword low at the right
              spine=(4, 0, 0), head=(-4, 0, 0))
    hold = (R_SHIELD, R_SWORD)
    out = []
    out.append(clip(rig, "Idle", [K(1, GUARD), K(30, add(GUARD, P(head=(0, 6, 0), chest=(-1, 0, 0)))),
                                  K(60, add(GUARD, P(head=(0, -6, 0)))), K(90, GUARD)], loop=True, aims=hold))
    # Walk: a heavy armoured stride. 48-frame cycle.
    def stomp(s):
        return P(GUARD, {"thigh.L": (18 * s, 0, 4), "shin.L": (-10 if s > 0 else -24, 0, 0), "foot.L": (8 * s, 0, 0)},
                 {"thigh.R": (-18 * s, 0, -4), "shin.R": (-24 if s > 0 else -10, 0, 0), "foot.R": (-8 * s, 0, 0)},
                 spine=(6, 0, 0), chest=(0, -6 * s, 0), hips=(0, 6 * s, 0))
    def lift(leg):
        o = "R" if leg == "L" else "L"; side = 1 if leg == "L" else -1
        return P(GUARD, {f"thigh.{leg}": (40, 0, 0), f"shin.{leg}": (-60, 0, 0), f"thigh.{o}": (0, 0, 0), f"shin.{o}": (-8, 0, 0)},
                 spine=(6, 0, 6 * side), chest=(0, 0, 3 * side), head=(0, 0, -4 * side))
    out.append(clip(rig, "Walk", [K(1, stomp(1)), K(13, lift("R")), K(25, stomp(-1)), K(37, lift("L")), K(49, stomp(1))],
                    loop=True, aims=hold))
    # Charge / Attack: running hard behind the shield, sword arm pumping; the shield (left shoulder leading) slams
    # into the target on frame 16 and the rook drives on through
    def stride(s, lean):
        a, b = ("L", "R") if s > 0 else ("R", "L")
        return P(ARMS(upper_arm_L=(0.55, -0.45, -0.7), forearm_L=(-0.4, -0.85, 0.3),
                      upper_arm_R=(-0.5, -0.2 - 0.35 * s, -0.84), forearm_R=(-0.1, -0.85 - 0.1 * s, 0.4)),
                 {f"thigh.{a}": (60, 0, 0), f"shin.{a}": (-40, 0, 0), f"foot.{a}": (-10, 0, 0),
                  f"thigh.{b}": (-30, 0, 0), f"shin.{b}": (-30, 0, 0), f"foot.{b}": (40, 0, 0)},
                 spine=(lean, 0, 0), chest=(lean * 0.3, -8 * s, 0), hips=(0, 10 * s, 0), head=(-lean * 0.6, 0, 0))
    run_aims = [("shield", "strap", (0.15, -1, 0)), ("weapon", (-0.3, 0.4, 0.85), (1, 0, 0))]
    def run(s): return stride(s, 34)
    out.append(clip(rig, "Charge", [
        K(1, run(1), aims=run_aims), K(5, add(run(-1), P(thigh_L=(-20, 0, 0), thigh_R=(-20, 0, 0))), (0, 0, 0.02), aims=run_aims),
        K(9, run(-1), aims=run_aims), K(13, add(run(1), P(thigh_L=(-20, 0, 0), thigh_R=(-20, 0, 0))), (0, 0, 0.02), aims=run_aims),
        K(17, run(1), aims=run_aims)], loop=True, flowing=True, aims=hold))
    tackle = P(ARMS(upper_arm_L=(0.75, -0.55, -0.35), forearm_L=(-0.3, -0.85, 0.4), upper_arm_R=(-0.55, 0.2, -0.8), forearm_R=(-0.1, -0.6, 0.8)),
               {"thigh.L": (64, 0, 4), "shin.L": (-30, 0, 0), "foot.L": (-14, 0, 0), "thigh.R": (-44, 0, -4), "shin.R": (-12, 0, 0), "foot.R": (50, 0, 0)},
               spine=(46, -26, 0), chest=(14, -14, 0), head=(-34, 10, 0))   # left shoulder and shield lead, head down
    slam = [("shield", "strap", (0.0, -1, 0.1)), ("weapon", (-0.3, 0.5, 0.8), (1, 0, 0))]
    L = ROOK_LUNGE
    out.append(clip(rig, "Attack", [
        K(1, run(1), aims=run_aims), K(5, run(-1), (0, L * 0.25, 0.02), aims=run_aims), K(9, stride(1, 38), (0, L * 0.5, 0), aims=run_aims),
        K(13, stride(-1, 42), (0, L * 0.75, 0), aims=run_aims),
        K(16, tackle, (0, L, 0), aims=slam), K(19, add(tackle, P(spine=(6, 0, 0))), (0, L - 0.07, 0), aims=slam),
        K(25, stride(1, 22), (0, L - 0.1, 0), aims=run_aims), K(32, GUARD, (0, L - 0.1, 0)), K(42, GUARD, (0, L - 0.1, 0))],
        aims=hold, flowing=True))
    # Iai (sheet "ルーク | 居合モーション", 28 beats). 予備動作: 立ち姿 / 視線を定める / 右手を柄に添える / 重心を落とす / 左手で鞘を
    # 固定 / 呼吸を整える. 抜刀: 体をひねり柄を引く / 鞘を引き抜き始める / 刀が鞘から離れる / 抜刀完了 / 斬撃に入る / 上段の構え.
    # 斬撃: 斬り下ろし開始 / 最大振り下ろし / 軌跡最大 / 斬り抜ける / フォロースルー / 振り切り - the rook bursts past the pawn on its
    # left and the blade goes through on IAI_HIT. 残心: 姿勢 / 視線を保つ / 呼吸を整える / 軽く姿勢を戻す. 納刀: 刀を鞘へ向ける /
    # 刃を鞘に当てる / 納刀(半ば) / 納刀(完了) / 左手を離す / 通常構えに戻る. Ends ROOK_IAI_END from where it started.
    k = 0.34 / 0.7   # board units -> authoring units for the root
    sx, past = ROOK_IAI_END
    H = IAI_HIT
    rest = P(STAND, ARMS(upper_arm_R=(-0.1, -0.4, -0.9), forearm_R=(0.8, -0.5, -0.3)), ARMS(upper_arm_L=(0.35, -0.35, -0.87), forearm_L=(-0.8, -0.5, 0.2)),
             spine=(4, 0, 0), head=(-4, 0, 0))   # right hand across to the hilt at the left hip (IK'd onto hilt.R)
    gaze = add(rest, P(head=(-8, -6, 0), spine=(4, 0, 0)))
    sink = add(rest, P(spine=(10, 0, 0), thigh_L=(16, 0, 0), shin_L=(-26, 0, 0), thigh_R=(-2, 0, 0), shin_R=(-20, 0, 0), foot_R=(14, 0, 0)))
    fix = add(sink, P(ARMS(upper_arm_L=(0.25, -0.2, -0.95), forearm_L=(-0.6, -0.6, -0.5))))    # shield hand down to the scabbard
    breath = add(fix, P(chest=(-3, 0, 0)))
    twist = add(fix, P(spine=(4, 22, 0), chest=(0, 10, 0), head=(0, -18, 0)))
    pull = P(fix, ARMS(upper_arm_R=(0.1, -0.6, -0.2), forearm_R=(-0.3, -0.5, 0.8)), spine=(10, 30, 0), head=(-10, -20, 0))
    drawn = P(fix, ARMS(upper_arm_R=(-0.7, -0.3, 0.25), forearm_R=(-0.5, -0.5, 0.7)), spine=(6, -10, 0), head=(-12, 0, 0))
    jodan = P({"thigh.L": (34, 0, 8), "shin.L": (-56, 0, 0), "foot.L": (22, 0, 0), "thigh.R": (-6, 0, -8), "shin.R": (-40, 0, 0), "foot.R": (34, 0, 0)},
              ARMS(upper_arm_R=(-0.3, 0.0, 0.95), forearm_R=(0.2, 0.3, 0.92), upper_arm_L=(0.4, -0.2, -0.88), forearm_L=(-0.2, -0.9, 0.3)),
              spine=(16, -10, 0), chest=(4, -6, 0), head=(-18, 10, 0))
    dash = P({"thigh.L": (60, 0, 6), "shin.L": (-30, 0, 0), "foot.L": (-10, 0, 0), "thigh.R": (-40, 0, -6), "shin.R": (-20, 0, 0), "foot.R": (44, 0, 0)},
             ARMS(upper_arm_R=(-0.25, -0.5, 0.8), forearm_R=(0.2, -0.3, 0.92), upper_arm_L=(0.5, 0.1, -0.85), forearm_L=(0.2, -0.8, 0.5)),
             spine=(36, -10, 0), chest=(10, -6, 0), head=(-30, 10, 0))
    cut = P({"thigh.L": (54, 0, 6), "shin.L": (-40, 0, 0), "foot.L": (0, 0, 0), "thigh.R": (-36, 0, -6), "shin.R": (-16, 0, 0), "foot.R": (40, 0, 0)},
            ARMS(upper_arm_R=(-0.35, -0.93, -0.1), forearm_R=(-0.35, -0.93, 0.05), upper_arm_L=(0.6, 0.2, -0.75), forearm_L=(0.5, -0.4, 0.5)),
            spine=(30, 12, 0), chest=(8, 8, 0), head=(-24, -14, 0))   # arm thrown out to the right-front, toward the pawn
    through = P({"thigh.L": (40, 0, 8), "shin.L": (-60, 0, 0), "foot.L": (20, 0, 0), "thigh.R": (-20, 0, -8), "shin.R": (-30, 0, 0), "foot.R": (36, 0, 0)},
                ARMS(upper_arm_R=(-0.95, 0.1, -0.1), forearm_R=(-1, 0.2, 0.1), upper_arm_L=(0.6, 0.2, -0.75), forearm_L=(0.5, -0.4, 0.5)),
                spine=(28, 30, 0), chest=(6, 14, 0), head=(-20, -20, 0))
    zanshin = add(through, P(spine=(-10, -6, 0), head=(6, 10, 0)))
    to_sheath = P(fix, ARMS(upper_arm_R=(-0.2, -0.6, -0.3), forearm_R=(0.7, -0.6, -0.2)), spine=(6, 10, 0), head=(4, -6, 0))
    sheathed = [("weapon", (0.3, 0.92, 0.1), (0, 0, 1))]
    end = (sx * k, past * k, 0)
    out.append(clip(rig, "Iai", [
        K(1, rest), K(8, gaze), K(14, add(gaze, P(spine=(2, 0, 0)))), K(20, sink, (0, 0.01, 0)), K(26, fix, (0, 0.01, 0)),
        K(32, breath, (0, 0.01, 0)), K(36, twist, (0, 0.02, 0)), K(40, pull, (0, 0.02, 0), aims=[("weapon", (0.3, -0.4, 0.86), (1, 0, 0))]),
        K(44, drawn, (0, 0.02, 0), aims=[("weapon", (-0.55, -0.45, 0.7), (1, 0, 0))]),
        K(48, add(drawn, P(spine=(6, 0, 0))), (0, 0.03, 0), aims=[("weapon", (-0.3, -0.6, 0.74), (1, 0, 0))]),
        K(H - 8, jodan, (0, 0.03, 0), aims=[("weapon", (0, 0.5, 0.86), (1, 0, 0))]),
        K(H - 2, dash, (sx * 1.13 * k, -IAI_CUT_Y * 0.7 * k, 0), aims=[("weapon", (-0.2, -0.3, 0.93), (1, 0, 0))]),   # wide of its blades...
        K(H, cut, (sx * 0.87 * k, -IAI_CUT_Y * k, 0), aims=[("weapon", "target", T_IAI)]),   # ...and in close as it comes level
        K(H + 4, through, (sx * k, -1.6 * k, 0), aims=[("weapon", (-0.85, -0.45, 0.1), (0, 0, 1))]),   # carried on round to the right
        K(H + 8, through, (sx * k, -2.2 * k, 0), aims=[("weapon", (-0.95, 0.2, -0.1), (0, 0, 1))]),
        K(H + 12, through, end, aims=[("weapon", (-0.9, 0.1, -0.4), (0, 0, 1))]),
        K(H + 20, zanshin, end, aims=[("weapon", (-0.8, -0.3, -0.5), (1, 0, 0))]),
        K(H + 28, zanshin, end, aims=[("weapon", (-0.8, -0.3, -0.5), (1, 0, 0))]),
        K(H + 36, add(zanshin, P(chest=(-3, 0, 0))), end, aims=[("weapon", (-0.8, -0.3, -0.5), (1, 0, 0))]),
        K(H + 44, add(fix, P(spine=(4, 0, 0))), end, aims=[("weapon", (-0.4, -0.6, -0.7), (1, 0, 0))]),
        K(H + 50, to_sheath, end, aims=[("weapon", (0.5, 0.6, -0.1), (0, 0, 1))]),
        K(H + 54, rest, end), K(H + 58, rest, end), K(H + 62, rest, end), K(H + 66, add(rest, P(ARMS(upper_arm_L=(0.35, -0.35, -0.87), forearm_L=(-0.8, -0.5, 0.2)))), end),
        K(H + 72, rest, end)], aims=hold, flowing=True))
    IAI_SHEATH = {"R": [(1, 1), (38, 1), (43, 0), (H + 54, 0), (H + 62, 1)]}
    IAI_HILT = {"R": [(1, 1), (36, 1), (40, 0), (H + 52, 0), (H + 58, 1)]}
    # Block: shield raised square to the attacker, sword drawn back ready
    shield_up = P({"thigh.L": (26, 0, 3), "shin.L": (-42, 0, 0), "foot.L": (14, 0, 0), "thigh.R": (-14, 0, -3), "shin.R": (-18, 0, 0), "foot.R": (30, 0, 0)},
                  ARMS(upper_arm_L=(0.4, -0.55, -0.73), forearm_L=(-0.85, -0.45, 0.25),
                       upper_arm_R=(-0.3, 0.2, -0.93), forearm_R=(-0.05, -0.9, 0.4)),
                  spine=(12, 0, 0), chest=(4, 0, 0), head=(-8, 0, 0))
    up = [("shield", "strap", (0.1, -1, 0)), ("weapon", (-0.1, -0.3, 0.95), (1, 0, 0))]
    absorbed = add(shield_up, P(spine=(-8, 0, 0), head=(-10, 0, 0)))
    out.append(clip(rig, "Block", [K(1, GUARD), K(9, shield_up, aims=up), K(16, shield_up, aims=up),
                                   K(18, absorbed, (0, 0.04, 0), aims=up), K(26, shield_up, (0, 0.03, 0), aims=up), K(36, GUARD)],
                    aims=hold, flowing=True))
    reel = add(absorbed, P(spine=(-14, 0, 6), head=(-12, 8, 0), thigh_L=(-12, 0, 0), thigh_R=(12, 0, 0), shin_R=(-26, 0, 0)))
    out.append(clip(rig, "Hit", [K(1, GUARD), K(9, shield_up, aims=up), K(16, shield_up, aims=up),
                                 K(19, reel, (0, 0.1, 0), (-5, 0, 3), aims=up), K(30, shield_up, (0, 0.1, 0), aims=up),
                                 K(44, GUARD, (0, 0.08, 0))], aims=hold, flowing=True))
    # Death: the shield is smashed aside, the knight topples backwards like a felled keep
    flung = add(shield_up, P(ARMS(upper_arm_L=(0.85, -0.15, -0.5), forearm_L=(0.75, -0.55, 0.35)), spine=(-6, 0, 0)))
    tilt = add(flung, P(spine=(-20, 0, 10), head=(-20, 0, 10)))
    fallen = P(STAND, ARMS(upper_arm_L=(0.6, 0, -0.8), forearm_L=(0.6, 0.3, -0.7), upper_arm_R=(-0.6, 0, -0.8), forearm_R=(-0.6, 0.3, -0.7)),
               spine=(-10, 0, 0), head=(-15, 0, 15))
    free = [("weapon", None, None)]
    out.append(clip(rig, "Death", [K(1, GUARD), K(9, shield_up, aims=up), K(14, shield_up, aims=up), K(18, tilt, (0, 0.06, 0), (-8, 0, 6)),
                                   K(30, tilt, (0, 0.1, 0), (-25, 0, 10), aims=free), K(42, fallen, (0, 0.3, 0.05), (-85, 0, 10), aims=free),
                                   K(46, fallen, (0, 0.31, 0.07), (-80, 0, 10), aims=free), K(52, fallen, (0, 0.31, 0.05), (-85, 0, 10), aims=free),
                                   K(72, fallen, (0, 0.31, 0.05), (-85, 0, 10), aims=free)], aims=hold))
    # Victory: sword thrust to the sky, shield lowered
    cheer = P(STAND, ARMS(upper_arm_R=(-0.45, -0.1, 0.88), forearm_R=(-0.05, -0.15, 0.99),
                          upper_arm_L=(0.32, -0.1, -0.94), forearm_L=(0.25, -0.55, -0.8)), spine=(-6, 0, 0), head=(-14, 0, 0))
    sky = [("weapon", (0, 0.1, 1), (1, 0, 0))]
    out.append(clip(rig, "Victory", [K(1, GUARD), K(10, cheer, aims=sky), K(18, add(cheer, P(spine=(-4, 0, 0))), aims=sky),
                                     K(30, cheer, aims=sky), K(48, GUARD)], aims=hold, flowing=True))
    for a in out:
        if a.name.endswith("|Iai"):   # the blade lives in the scabbard before the draw and after the sheathing
            hilt_ik(rig, a, IAI_HILT)
            sheath_pass(rig, a, IAI_SHEATH)
            natural_wrist(rig, a, "hand.R", "weapon", lambda f: ramp(IAI_SHEATH["R"], f) > 0, edge=True)
        else:
            sheath_pass(rig, a, {"R": [(1, 0)]})   # keys the sword in the fist so no clip inherits the sheathed pose
            natural_wrist(rig, a, "hand.R", "weapon", edge=True)
    return out

CLIPS["Rook"] = rook_clips
