# Knight clips (exec'd after anims.py). The mounted knight with sword and kite shield (detailed sheet "ナイト | 詳細
# モーション・攻撃シーン", 2026-10-25; was a lance). Contact frames are solved in Blender (KN_LUNGE) so every cut lands where it
# should: on the pawn's crossed blades (T_GUARD, pawn KN_DUEL squares ahead) or, for the kills, through its chest.
# Horse conventions (probed): leg bones +X swing the lower end forward; h_neck1 +X lowers the head,
# h_head +X lifts the muzzle; h_tail1 +X swings the tail forward / Z sideways.
# Rearing rotates the whole statue about the hind hooves (rear()); the rider is parented to the horse's back.

GROUND_CFG["Knight"] = ((("h_fhoof", "tail", 0.0), ("h_hhoof", "tail", 0.0)), "h_hips")
STANCE_FEET = {"Knight": "h_fhoof"}
KN_SCALE = 0.47
KN_HIND_Y = 0.55 * KN_SCALE          # hind hooves, board units behind the root
KN_DUEL = 1.0                         # the knight fights a pawn one square ahead (T_GUARD / T_CHEST as for the pawns)
KN_CUT = (KN_BLADE + KN_BALL * 0.8) * KN_SCALE   # board units from the bone head (grip) to the centre of the spiked ball
KN_REACH_TIP = KN_CUT + KN_BALL * KN_SCALE        # ... to the front of the ball (kills: the ball goes into the chest)
# (clip, frame) -> root lunge (authoring units) solved so the cut lands on its target
KN_LUNGE = {('Combo', 8): -0.0741, ('Combo', 13): -0.1238, ('Combo', 18): -0.0744, ('Combo', 23): -0.0741, ('Combo', 28): -0.1236, ('Combo', 33): -0.1237, ('Combo', 38): -0.1241, ('Combo', 45): -0.074, ('Skill', 22): -0.074, ('Skill', 28): -0.124, ('Skill', 36): -0.3091, ('AttackBlocked', 16): -0.0745, ('LeapAttack', 30): -0.427, ('Attack', 20): -0.0978, ('Attack', 26): -0.0745, ('Attack', 32): -0.1237, ('Attack', 40): -0.3066, ('Sweep', 24): -0.1545}
# kills from horseback: the point of the sword (not the cutting edge) goes into the front of the chest - the rider sits
# ~0.55 squares behind the horse's nose, so a deeper target would drive the horse into the pawn
T_KN_KILL = (0.0, -0.93, 0.7)

def rear(deg):
    """Root (loc, rot) that tips the statue nose-up by deg about its hind hooves."""
    t = math.radians(deg)
    k = LOC_REF / KN_SCALE   # clip() scales root offsets by piece_scale / LOC_REF
    return (0, KN_HIND_Y * (1 - math.cos(t)) * k, KN_HIND_Y * math.sin(t) * k), (-deg, 0, 0)

SWORD_UP = ("weapon", (0, -0.35, 0.94), (1, 0, 0))
SWORD_SKY = ("weapon", (0, 0.1, 1), (1, 0, 0))
KN_SHIELD = ("shield", "strap", (0.35, -1, 0))

RIDE = P(ARMS(upper_arm_R=(-0.2, -0.2, -0.96), forearm_R=(-0.05, -0.85, 0.5),        # sword held up at the right
              upper_arm_L=(0.35, -0.35, -0.87), forearm_L=(-0.8, -0.5, 0.2)),         # shield across the front
         spine=(4, 0, 0), head=(-4, 0, 0))

def horse(**b):
    """Horse pose from short names: fu/fo/fc = foreleg upper/forearm/cannon, th/ga/hc = hind thigh/gaskin/cannon."""
    names = {"fu": "h_fupper", "fo": "h_fore", "fc": "h_fcannon", "th": "h_thigh", "ga": "h_gaskin", "hc": "h_hcannon",
             "ff": "h_fhoof", "hf": "h_hhoof"}
    out = {}
    for k, v in b.items():
        if k[-2:] in ("_L", "_R"):
            out[f"{names[k[:-2]]}.{k[-1]}"] = (v, 0, 0)
        else:
            out[{"neck": "h_neck1", "neck2": "h_neck2", "head": "h_head", "tail": "h_tail1", "tail2": "h_tail2",
                 "back": "h_hips", "chest": "h_chest"}[k]] = v
    return out

# the standard 12-beat combo (sheet "通常攻撃コンボ"): (frame, style); every cut lands on the pawn's crossed blades
KN_COMBO = list(zip(KNIGHT_COMBO_FRAMES, ("up", "side", "down", "thrust", "side", "spin", "spin", "leap")))   # frames: anims.py
# the skill (sheet "スキル攻撃"): two blows of light caught on the guard, then the wide sweep that kills
KN_SKILL_GUARD, KN_SKILL_KILL = KNIGHT_SKILL_GUARD, KNIGHT_SKILL_KILL
KN_SWEEP_KILL = 24   # Sweep: the morning star goes through the pawn on this frame
# the sweep is swung out to the knight's right (its weapon side): the pawn stands at the right front, clear of the
# horse's head (standing straight ahead it was trampled). KN_SWEEP_PAWN: the pawn's place in clip space (x: -right)
KN_SWEEP_PAWN = (-0.55, -0.62)
_d = math.hypot(*KN_SWEEP_PAWN)
T_KN_SWEEP = (KN_SWEEP_PAWN[0] * (1 - 0.12 / _d), KN_SWEEP_PAWN[1] * (1 - 0.12 / _d), 0.7)   # the front of its chest

def knight_clips(rig):
    out = []
    hold = (SWORD_UP, KN_SHIELD)
    up = LOC_REF / KN_SCALE
    def lunge(name, f, default=-0.05): return KN_LUNGE.get((name, f), default)
    # ---- Idle (sheet: 構え / 周囲を見渡す / 馬が足を踏み替える / 剣を軽く上げる / 盾を整える / マントの揺れ / 再び構える / 呼吸・静止)
    out.append(clip(rig, "Idle", [
        K(1, RIDE),
        K(13, P(RIDE, horse(neck=(4, 0, 0), head=(-6, 0, 10)), head=(0, 22, 0), chest=(0, 6, 0))),
        K(25, P(RIDE, horse(neck=(-6, 0, 0), head=(8, 0, 0), fu_L=30, fo_L=-10, fc_L=-60, tail=(0, 0, -10)))),
        K(37, P(RIDE, ARMS(upper_arm_R=(-0.25, -0.3, -0.92), forearm_R=(-0.1, -0.5, 0.86)), horse(fu_L=8, fc_L=-12)),
          aims=[("weapon", (0, -0.15, 1), (1, 0, 0))]),
        K(49, P(RIDE, ARMS(forearm_L=(-0.85, -0.45, 0.28)), head=(0, -10, 0), spine=(2, 0, 0)), aims=[("shield", "strap", (0.2, -1, 0))]),
        K(61, P(RIDE, horse(tail=(4, 0, 12), neck=(2, 0, 0)), spine=(6, 0, -3), chest=(-2, 0, 0))),
        K(73, RIDE), K(85, P(RIDE, chest=(-2, 0, 0), head=(-6, 0, 0))), K(96, RIDE)], loop=True, aims=hold, flowing=True))

    # ---- Walk: slow diagonal-pair walk (left-fore + right-hind together), 48-frame cycle, head nods with the stride
    def stride(s):
        a, b = ("L", "R") if s > 0 else ("R", "L")
        return P(RIDE, horse(**{f"fu_{a}": 16, f"fc_{a}": 4, f"th_{b}": 14, f"hc_{b}": 6,
                                f"fu_{b}": -14, f"fc_{b}": 8, f"th_{a}": -16, f"hc_{a}": -4,
                                "neck": (5, 0, 0), "head": (-4, 0, 0), "tail": (2, 0, 4 * s)}),
                 spine=(4, 3 * s, 0))
    def swing(lift):
        o = "R" if lift == "L" else "L"
        return P(RIDE, horse(**{f"fu_{o}": 22, f"fo_{o}": 10, f"fc_{o}": -70, f"th_{lift}": 22, f"ga_{lift}": -20, f"hc_{lift}": 40,
                                f"fu_{lift}": -4, f"th_{o}": -4, "neck": (-3, 0, 0), "head": (2, 0, 0)}),
                 spine=(2, 0, 0))
    out.append(clip(rig, "Walk", [K(1, stride(1)), K(13, swing("L")), K(25, stride(-1)), K(37, swing("R")), K(49, stride(1))],
                    loop=True, aims=hold))

    # ---- Draw (sheet "抜刀モーション"): 右手で柄に触れる / 抜刀し始める / 剣が鞘から出る / 抜刀完了 / 構えに移行 / 構え
    sheathed_rest = P(RIDE, ARMS(upper_arm_R=(-0.1, -0.4, -0.9), forearm_R=(0.8, -0.5, -0.3)))
    pull = P(RIDE, ARMS(upper_arm_R=(0.1, -0.6, -0.2), forearm_R=(-0.3, -0.5, 0.8)), spine=(0, 14, 0))
    flourish = P(RIDE, ARMS(upper_arm_R=(-0.7, -0.2, 0.3), forearm_R=(-0.5, -0.4, 0.75)), spine=(0, -8, 0))
    out.append(clip(rig, "Draw", [
        K(1, sheathed_rest), K(5, add(sheathed_rest, P(spine=(6, 10, 0)))), K(9, pull, aims=[("weapon", (0.3, -0.4, 0.86), (1, 0, 0))]),
        K(13, flourish, aims=[("weapon", (-0.6, -0.3, 0.75), (1, 0, 0))]), K(19, RIDE), K(24, RIDE)], aims=hold, flowing=True))

    # ---- the cut poses used by the combo, the skill and the single Attack
    cut_arm = ARMS(upper_arm_R=(-0.15, -0.95, 0.1), forearm_R=(0.25, -0.95, 0.0))
    lean_in = horse(fu_L=-6, fu_R=-6, th_L=10, th_R=10, neck=(8, 0, 22), head=(-6, 0, 10))   # head turned aside for the blade
    def cut(twist=0, lean=18): return P(RIDE, cut_arm, lean_in, spine=(lean, twist, 0), chest=(6, twist * 0.5, 0), head=(-14, 0, 0))
    winds = {
        "up": P(RIDE, ARMS(upper_arm_R=(-0.5, 0.2, -0.85), forearm_R=(-0.3, 0.4, -0.85)), spine=(6, 16, 0)),
        "side": P(RIDE, ARMS(upper_arm_R=(-0.85, 0.3, -0.2), forearm_R=(-0.6, 0.6, 0.4)), spine=(0, 26, 0)),
        "down": P(RIDE, ARMS(upper_arm_R=(-0.3, 0.0, 0.95), forearm_R=(0.2, 0.3, 0.92)), spine=(-10, 0, 0), head=(-10, 0, 0)),
        "thrust": P(RIDE, ARMS(upper_arm_R=(-0.35, 0.5, -0.8), forearm_R=(0.0, -0.95, 0.2)), spine=(-4, 18, 0)),
        "spin": P(RIDE, ARMS(upper_arm_R=(-0.95, 0.1, -0.1), forearm_R=(-1, 0.1, 0.1)), spine=(0, 40, 0), chest=(0, 14, 0)),
        "leap": P(RIDE, ARMS(upper_arm_R=(-0.3, 0.0, 0.95), forearm_R=(0.2, 0.3, 0.92)), spine=(-14, 0, 0)),
    }
    approach = {"up": (-0.4, -0.2, -0.9), "side": (-0.9, 0.4, 0.1), "down": (-0.1, 0.3, 0.95), "thrust": (0, -1, 0.1),
                "spin": (-1, 0.2, 0.0), "leap": (0, 0.3, 0.95)}
    on_guard = [("weapon", "target", T_GUARD)]
    shield_up = P(RIDE, ARMS(upper_arm_L=(0.4, -0.55, -0.73), forearm_L=(-0.85, -0.45, 0.25)),
                  horse(th_L=10, th_R=10, hc_L=8, hc_R=8, fu_L=-8, fu_R=-8, neck=(-10, 0, 0), head=(10, 0, 0)), spine=(6, 0, 0))
    guard_up = [("shield", "strap", (0.1, -1, 0))]

    # ---- Combo (sheet "通常攻撃コンボ" 12 beats): 構え / 斬り上げ / 横薙ぎ / 振り下ろし / 突き / 追撃斬り / 回転斬り(1)(2)
    #      / 飛び込み斬り / 着地 / 盾で受け流し / 再び構え
    keys, events, spun = [K(1, RIDE)], [], 0
    lr, rr = rear(14)
    for f, style in KN_COMBO:
        L = lunge("Combo", f)
        a = approach[style]
        rot_w = (0, 0, spun + 180) if style == "spin" else ((0, 0, spun) if spun else None)   # wound up facing away...
        if style == "spin": spun += 360                                                         # ...and round to face it again
        if style == "leap":
            keys.append(K(f - 4, P(winds["leap"], horse(fu_L=50, fo_L=10, fc_L=-80, fu_R=40, fo_R=6, fc_R=-70)),
                          tuple(x + y for x, y in zip(lr, (0, 0.02, 0))), rr, aims=[("weapon", a, (1, 0, 0))]))
        else:
            keys.append(K(f - 3, winds[style], (0, L * 0.5, 0), rot_w, aims=[("weapon", a, (1, 0, 0))]))
        keys.append(K(f, cut(twist=-14 if style in ("side", "spin") else 0), (0, L, 0), (0, 0, spun) if spun else None, aims=on_guard))
        events.append(f)
    keys += [K(50, P(cut(), horse(fu_L=4, fu_R=4, th_L=20, th_R=20, hc_L=16, hc_R=16)), (0, 0, 0), (0, 0, spun) if spun else None),
             K(55, shield_up, (0, 0.02, 0), (0, 0, spun) if spun else None, aims=guard_up),
             K(62, RIDE, (0, 0, 0), (0, 0, spun) if spun else None)]
    out.append(clip(rig, "Combo", keys, aims=hold, flowing=True))
    KN_EVENTS["Combo"] = events

    # ---- Skill (sheet "スキル攻撃" 10 beats): 発動の構え / 馬が駆け上がる / 剣に光が集まる / 光の斬撃(1)(2) / 広範囲回転薙ぎ払い
    #      / 衝撃波 / 光の余波 / 収束 / 終了・構え. The viewer draws the light; the sweep kills on KN_SKILL_KILL.
    r1, q1 = rear(24)
    raised = P(RIDE, ARMS(upper_arm_R=(-0.15, -0.1, 0.98), forearm_R=(0.1, -0.1, 0.99)),
               horse(fu_L=70, fo_L=20, fc_L=-110, fu_R=55, fo_R=15, fc_R=-95, th_L=-30, th_R=-30, hc_L=20, hc_R=20,
                     neck=(-20, 0, 0), head=(16, 0, 0), tail=(-30, 0, 0)), spine=(-6, 0, 0), head=(-16, 0, 0))
    g1, g2 = KN_SKILL_GUARD
    out.append(clip(rig, "Skill", [
        K(1, RIDE), K(6, add(RIDE, P(spine=(8, 0, 0))), aims=[("weapon", (0, -0.3, 0.95), (1, 0, 0))]),
        K(12, raised, r1, q1, aims=[SWORD_SKY]), K(18, raised, r1, q1, aims=[SWORD_SKY]),
        K(g1 - 2, winds["down"], (0, lunge("Skill", g1) * 0.5, 0), aims=[("weapon", approach["down"], (1, 0, 0))]),
        K(g1, cut(), (0, lunge("Skill", g1), 0), aims=on_guard),
        K(g2 - 2, winds["side"], (0, lunge("Skill", g2) * 0.5, 0), aims=[("weapon", approach["side"], (1, 0, 0))]),
        K(g2, cut(twist=-14), (0, lunge("Skill", g2), 0), aims=on_guard),
        K(KN_SKILL_KILL - 3, winds["spin"], (0, lunge("Skill", KN_SKILL_KILL) * 0.5, 0), aims=[("weapon", approach["spin"], (1, 0, 0))]),
        K(KN_SKILL_KILL, cut(twist=-20, lean=22), (0, lunge("Skill", KN_SKILL_KILL), 0), aims=[("weapon", "target", T_KN_KILL)]),
        K(KN_SKILL_KILL + 4, P(RIDE, ARMS(upper_arm_R=(-0.9, 0.3, -0.2), forearm_R=(-0.8, 0.5, 0.2)), spine=(10, -30, 0)),
          (0, lunge("Skill", KN_SKILL_KILL), 0), aims=[("weapon", (-0.9, 0.4, 0.1), (1, 0, 0))]),
        K(50, add(RIDE, P(spine=(6, 0, 0))), (0, lunge("Skill", KN_SKILL_KILL) * 0.6, 0)),
        K(60, RIDE)], aims=hold, flowing=True))

    gather = P(RIDE, horse(th_L=18, th_R=14, ga_L=-14, ga_R=-10, hc_L=12, hc_R=10, fu_L=-6, fu_R=-6, neck=(-8, 0, 0), head=(6, 0, 0)),
               spine=(-6, 0, 0))
    # ---- Attack (sheet "攻撃モーション" 16 beats, morning star): 構え / 馬を踏み込ませる / 武器を振り上げる / 上段へ振りかぶる
    #      / 振り下ろし開始 / 斜めに叩き込む / 衝撃エフェクト / 跳ね上げる / 追撃で横薙ぎ / 回転して薙ぎ払う / 斬撃の余韻
    #      / 馬を立て直す / 武器を戻す / 納めの動作 / 残心 / 元の構え. The smash, the upswing and the sweep are taken on the pawn's
    #      X (KNIGHT_MACE_GUARD); the spinning sweep kills (KNIGHT_MACE_KILL).
    g1, g2, g3 = KNIGHT_MACE_GUARD; kk = KNIGHT_MACE_KILL
    rest_sh = P(RIDE, ARMS(upper_arm_R=(-0.3, 0.1, -0.2), forearm_R=(0.3, 0.3, 0.9)))   # weapon shouldered
    l4, r4 = rear(12)
    out.append(clip(rig, "Attack", [
        K(1, RIDE), K(6, gather, (0, 0.03, 0)), K(10, winds["up"], (0, 0.02, 0), aims=[("weapon", (-0.3, 0.3, 0.9), (1, 0, 0))]),
        K(14, winds["down"], (0, lunge("Attack", g1) * 0.3, 0), aims=[("weapon", (0, 0.6, 0.8), (1, 0, 0))]),
        K(17, winds["down"], (0, lunge("Attack", g1) * 0.6, 0), aims=[("weapon", (-0.2, 0.2, 0.96), (1, 0, 0))]),
        K(g1, cut(twist=-8), (0, lunge("Attack", g1), 0), aims=on_guard),
        K(g1 + 2, cut(twist=-8), (0, lunge("Attack", g1), 0), aims=on_guard),
        K(g2 - 3, winds["up"], (0, lunge("Attack", g2) * 0.5, 0), aims=[("weapon", approach["up"], (1, 0, 0))]),
        K(g2, cut(), (0, lunge("Attack", g2), 0), aims=on_guard),
        K(g3 - 3, winds["side"], (0, lunge("Attack", g3) * 0.5, 0), aims=[("weapon", approach["side"], (1, 0, 0))]),
        K(g3, cut(twist=-14), (0, lunge("Attack", g3), 0), aims=on_guard),
        K(kk - 4, winds["spin"], (0, lunge("Attack", kk) * 0.5, 0), (0, 0, 180), aims=[("weapon", approach["spin"], (1, 0, 0))]),
        K(kk, cut(twist=-20, lean=22), (0, lunge("Attack", kk), 0), (0, 0, 360), aims=[("weapon", "target", T_KN_KILL)]),
        K(kk + 6, P(RIDE, ARMS(upper_arm_R=(-0.9, 0.3, -0.2), forearm_R=(-0.8, 0.5, 0.2)), spine=(10, -30, 0)),
          (0, lunge("Attack", kk), 0), (0, 0, 360), aims=[("weapon", (-0.9, 0.4, 0.1), (1, 0, 0))]),
        K(52, P(RIDE, horse(fu_L=40, fo_L=10, fc_L=-70, fu_R=30, fo_R=6, fc_R=-60, neck=(-12, 0, 0), head=(10, 0, 0))),
          tuple(a + b for a, b in zip(l4, (0, lunge("Attack", kk) * 0.6, 0))), (r4[0], 0, 360)),
        K(58, RIDE, (0, lunge("Attack", kk) * 0.3, 0), (0, 0, 360)), K(64, rest_sh, (0, 0, 0), (0, 0, 360), aims=[("weapon", (0.1, 0.5, 0.86), (1, 0, 0))]),
        K(70, add(rest_sh, P(head=(8, 0, 0))), (0, 0, 0), (0, 0, 360), aims=[("weapon", (0.1, 0.5, 0.86), (1, 0, 0))]),
        K(78, RIDE, (0, 0, 0), (0, 0, 360))], aims=hold, flowing=True))
    # ---- Sweep (user: "ナイトの攻撃は豪快な一払い"): the horse gathers, the knight hauls the morning star far back over his
    #      right shoulder, the whole statue twisting away, then unwinds into one huge horizontal sweep that takes the
    #      pawn on KN_SWEEP_KILL and carries on round; the horse rears on the follow-through and settles.
    S = KN_SWEEP_KILL; Ls = lunge("Sweep", S)
    haul = P(RIDE, ARMS(upper_arm_R=(-0.9, 0.4, 0.1), forearm_R=(-0.5, 0.8, 0.3)), gather, spine=(-4, 46, 0), chest=(0, 20, 0), head=(0, -30, 0))
    after = P(RIDE, ARMS(upper_arm_R=(0.6, -0.6, 0.0), forearm_R=(0.8, 0.2, 0.2)), spine=(16, -46, 0), chest=(6, -20, 0), head=(-10, 20, 0))
    l5, r5 = rear(18)
    out.append(clip(rig, "Sweep", [
        K(1, RIDE), K(6, gather, (0, 0.03, 0)),
        K(12, haul, (0, 0.04, 0), (0, 0, 25), aims=[("weapon", (-0.4, 0.85, 0.35), (1, 0, 0))]),
        K(16, haul, (0, 0.04, 0), (0, 0, 30), aims=[("weapon", (-0.2, 0.95, 0.25), (1, 0, 0))]),
        K(S - 3, winds["side"], (0, Ls * 0.5, 0), (0, 0, 12), aims=[("weapon", (-0.95, 0.2, 0.15), (1, 0, 0))]),
        K(S, P(cut(twist=-24, lean=14), ARMS(upper_arm_R=(-0.8, -0.55, -0.1), forearm_R=(-0.6, -0.8, 0.0))), (0, Ls, 0), (0, 0, 0),
          aims=[("weapon", "target", T_KN_SWEEP)]),   # arm thrown out to the right-front
        K(S + 4, after, (0, Ls, 0), (0, 0, -25), aims=[("weapon", (0.95, 0.1, 0.1), (1, 0, 0))]),
        K(S + 10, P(after, horse(fu_L=60, fo_L=16, fc_L=-100, fu_R=48, fo_R=12, fc_R=-90, neck=(-18, 0, 0), head=(14, 0, 0))),
          tuple(a + b for a, b in zip(l5, (0, Ls * 0.8, 0))), (r5[0], 0, -25), aims=[("weapon", (0.6, 0.6, 0.5), (1, 0, 0))]),
        K(S + 22, P(RIDE, ARMS(upper_arm_R=(-0.3, 0.1, -0.2), forearm_R=(0.3, 0.3, 0.9))), (0, Ls * 0.4, 0), (0, 0, -8),
          aims=[("weapon", (0.1, 0.5, 0.86), (1, 0, 0))]),
        K(S + 34, RIDE, (0, 0, 0), (0, 0, 0))], aims=hold, flowing=True))
    for name, target in (("AttackBlocked", T_GUARD),):
        L = lunge(name, 16)
        out.append(clip(rig, name, [
            K(1, RIDE), K(6, gather, (0, 0.04, 0)), K(12, winds["down"], (0, L * 0.5, 0), aims=[("weapon", approach["down"], (1, 0, 0))]),
            K(16, cut(), (0, L, 0), aims=[("weapon", "target", target)]),
            K(19 if name == "Attack" else 22, cut(), (0, L - (0.03 if name == "Attack" else -0.01), 0),
              aims=[("weapon", (0, -0.6, -0.8), (1, 0, 0))] if name == "Attack" else [("weapon", "target", target)]),
            K(30, RIDE, (0, L * 0.4, 0)), K(40, RIDE)], aims=hold, flowing=True))

    # ---- Block: shield up, the horse braces back on its haunches
    out.append(clip(rig, "Block", [K(1, RIDE), K(9, shield_up, aims=guard_up), K(16, shield_up, aims=guard_up),
                                   K(18, P(shield_up, spine=(-6, 0, 0)), (0, 0.06, 0), aims=guard_up), K(26, shield_up, (0, 0.04, 0), aims=guard_up),
                                   K(36, RIDE)], aims=hold, flowing=True))
    # ---- Hit (sheet "被撃" 6 beats): 受ける / よろめく / 体勢を崩す / 馬が踏み張る / 立て直す / 再び構え
    l2, r2 = rear(10)
    out.append(clip(rig, "Hit", [K(1, RIDE), K(9, shield_up, aims=guard_up), K(16, shield_up, aims=guard_up),
                                 K(20, P(shield_up, spine=(-18, 0, 8), head=(-12, 10, 0)), tuple(a + b for a, b in zip(l2, (0, 0.08, 0))), r2, aims=guard_up),
                                 K(26, P(shield_up, horse(th_L=24, th_R=24, hc_L=20, hc_R=20, fu_L=-14, fu_R=-14), spine=(-6, 0, -6)), (0, 0.1, 0), aims=guard_up),
                                 K(34, shield_up, (0, 0.09, 0), aims=guard_up), K(46, RIDE, (0, 0.06, 0))], aims=hold, flowing=True))
    # ---- Death (sheet "死亡" 6 beats): 致命傷を受ける / 馬から落下 / 落馬 / 倒れる / 動かない / 敗北
    knocked = P(RIDE, ARMS(upper_arm_L=(0.85, -0.1, -0.5), forearm_L=(0.6, -0.6, 0.5), upper_arm_R=(-0.6, 0.1, -0.6), forearm_R=(-0.4, -0.6, 0.5)),
                horse(neck=(-18, 0, 0), head=(14, 0, 0)), spine=(-20, 0, 6), head=(-20, 12, 0))
    kneel = P(knocked, horse(fu_L=-40, fo_L=-30, fc_L=100, fu_R=-35, fo_R=-25, fc_R=95, neck=(20, 0, 0), head=(-10, 0, 0)),
              spine=(25, 0, -10))
    down = P(kneel, horse(th_L=30, th_R=40, ga_L=-40, ga_R=-50, hc_L=50, hc_R=60, neck=(10, 0, 20), tail=(0, 0, 30)),
             spine=(10, 0, -30), head=(20, -30, 0))
    free = [("weapon", None, None)]
    out.append(clip(rig, "Death", [
        K(1, RIDE), K(9, shield_up, aims=guard_up), K(14, shield_up, aims=guard_up), K(17, knocked, (0, 0.08, 0), (-6, 0, 0)),
        K(28, kneel, (0, 0.06, -0.12), (14, 0, 0), aims=free),
        K(44, down, (0.1, 0.04, 0.02), (14, -80, 0), aims=free), K(48, down, (0.11, 0.04, 0.04), (14, -76, 0), aims=free),
        K(54, down, (0.11, 0.04, 0.02), (14, -80, 0), aims=free), K(78, down, (0.11, 0.04, 0.02), (14, -80, 0), aims=free)], aims=hold))
    # ---- Victory (sheet "勝利" 6 beats): 敵を見下ろす / 剣を掲げる / 馬が嘶く / マントの舞い / 静止 / 後ろ姿
    l3, r3 = rear(32)
    rearing = P(RIDE, ARMS(upper_arm_R=(-0.15, -0.1, 0.98), forearm_R=(0.1, -0.1, 0.99)),
                horse(fu_L=70, fo_L=20, fc_L=-110, fu_R=55, fo_R=15, fc_R=-95, th_L=-30, th_R=-30, hc_L=20, hc_R=20,
                      neck=(-20, 0, 0), head=(16, 0, 0), tail=(-30, 0, 0)), spine=(26, 0, 0), head=(-14, 0, 0))
    paw = P(rearing, horse(fu_L=50, fc_L=-80, fu_R=75, fc_R=-115))
    out.append(clip(rig, "Victory", [
        K(1, RIDE), K(8, P(RIDE, head=(14, 0, 0), spine=(6, 0, 0))), K(16, rearing, l3, r3, aims=[SWORD_SKY]),
        K(22, paw, l3, r3, aims=[SWORD_SKY]), K(28, rearing, l3, r3, aims=[SWORD_SKY]),
        K(40, P(RIDE, ARMS(upper_arm_R=(-0.15, -0.1, 0.98), forearm_R=(0.1, -0.1, 0.99))), aims=[SWORD_SKY]),
        K(54, P(RIDE, ARMS(upper_arm_R=(-0.15, -0.1, 0.98), forearm_R=(0.1, -0.1, 0.99))), aims=[SWORD_SKY])], aims=hold, flowing=True))
    out += leap_clips(rig, hold)
    for a in out:
        kind = a.name.split("|")[1]
        if kind == "Draw":   # the right hand rests on the hilt at the left hip, then draws (cross draw)
            hilt_ik(rig, a, {"R": [(1, 1), (5, 1), (8, 0)]})
            sheath_pass(rig, a, {"R": [(1, 1), (5, 1), (7, 0)]})
            natural_wrist(rig, a, "hand.R", "weapon", lambda f: f <= 5, KN_CUT)
        else:
            natural_wrist(rig, a, "hand.R", "weapon", tip=KN_CUT)
    return out

KN_EVENTS = {}

# ---- the knight's move (user: "目標のマスに滑空してそのマスに移動 / 相手の駒がいる場合は滑空して着地時に攻撃"):
# it gathers, springs and glides in an arc over the board along its L-move (sqrt 5 squares). The clip carries only
# the height and pitch; the game / viewer carries the knight across the board linearly from KN_TAKEOFF to KN_TOUCH.
#   Leap        -> lands on the target square.
#   LeapAttack  -> lands KN_LAND_SHORT squares short of the occupied square; on the way down (KN_LEAP_HIT) the sword
#                  is brought down through the defender, who crumbles; the knight then walks into the square.
KN_TAKEOFF, KN_TOUCH, KN_LEAP_HIT = 10, 34, 30
KN_MOVE = math.sqrt(5)
KN_LAND_SHORT = 0.6
KN_HIT_DIST = KN_MOVE - (KN_LEAP_HIT - KN_TAKEOFF) / (KN_TOUCH - KN_TAKEOFF) * (KN_MOVE - KN_LAND_SHORT)
T_KN_LEAP = (T_CHEST[0], -KN_HIT_DIST - 0.06, T_CHEST[2])   # the defender's chest at KN_LEAP_HIT, in clip space

def leap_clips(rig, hold):
    up = LOC_REF / KN_SCALE   # board units -> authoring units for root offsets
    def h(z): return (0, 0, z * up)
    crouch = P(RIDE, horse(th_L=26, th_R=22, ga_L=-24, ga_R=-20, hc_L=22, hc_R=18, fu_L=-8, fu_R=-8, fc_L=10, fc_R=10,
                           neck=(10, 0, 0), head=(-4, 0, 0), tail=(-6, 0, 0)), spine=(10, 0, 0))
    spring = P(RIDE, horse(fu_L=60, fo_L=20, fc_L=-110, fu_R=50, fo_R=16, fc_R=-100, th_L=-36, th_R=-40, ga_L=10, ga_R=10,
                           hc_L=-20, hc_R=-24, neck=(-12, 0, 0), head=(10, 0, 0), tail=(-30, 0, 0)), spine=(-6, 0, 0))
    glide = P(RIDE, horse(fu_L=70, fo_L=24, fc_L=-120, fu_R=66, fo_R=22, fc_R=-115, th_L=-50, th_R=-46, ga_L=14, ga_R=12,
                          hc_L=-26, hc_R=-24, neck=(8, 0, 0), head=(-8, 0, 0), tail=(-40, 0, 0)), spine=(12, 0, 0), head=(-10, 0, 0))
    reach = P(RIDE, horse(fu_L=34, fo_L=6, fc_L=-10, fu_R=40, fo_R=8, fc_R=-16, th_L=-20, th_R=-24, hc_L=-6, hc_R=-8,
                          neck=(12, 0, 0), head=(-6, 0, 0), tail=(-24, 0, 0)), spine=(8, 0, 0))   # forelegs out to land
    land = P(RIDE, horse(fu_L=10, fc_L=4, fu_R=14, fc_R=2, th_L=30, th_R=26, ga_L=-26, ga_R=-22, hc_L=26, hc_R=22,
                         neck=(16, 0, 0), head=(-8, 0, 0), tail=(-10, 0, 0)), spine=(14, 0, 0))
    lr, rr = rear(14)
    level = [SWORD_UP]
    def arc(mid, hit, rider_mid, rider_hit, lunge_y=0.0):
        return [K(1, RIDE), K(6, crouch, (0, 0.02, 0), aims=level),
                K(KN_TAKEOFF, spring, lr, rr, aims=level),
                K(15, P(glide, rider_mid), h(0.3), (-4, 0, 0), aims=mid),
                K(21, P(glide, rider_mid), h(0.48), (2, 0, 0), aims=mid),
                K(26, P(reach, rider_mid), h(0.36), (8, 0, 0), aims=mid),
                K(KN_LEAP_HIT, P(reach, rider_hit), (0, lunge_y, 0.18 * up), (10, 0, 0), aims=hit),
                K(KN_TOUCH, land, (0, 0, 0), (4, 0, 0), aims=level),
                K(40, P(land, horse(neck=(6, 0, 0))), (0, 0, 0), (0, 0, 0), aims=level), K(50, RIDE)]
    out = [clip(rig, "Leap", arc(level, level, {}, {}), aims=hold, flowing=True)]
    overhead = ARMS(upper_arm_R=(-0.3, 0.0, 0.95), forearm_R=(0.2, 0.3, 0.92))       # sword raised as it flies
    down_cut = ARMS(upper_arm_R=(-0.15, -0.95, 0.1), forearm_R=(0.25, -0.95, -0.1))  # brought down on the landing
    out.append(clip(rig, "LeapAttack", arc([("weapon", (0, 0.3, 0.95), (1, 0, 0))], [("weapon", "target", T_KN_LEAP)],
                                           overhead, down_cut, KN_LUNGE.get(("LeapAttack", KN_LEAP_HIT), 0.0)),
                    aims=hold, flowing=True))
    return out

CLIPS["Knight"] = knight_clips
