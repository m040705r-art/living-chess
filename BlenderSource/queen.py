# Queen: a crowned warrior-queen in a flowing gown and train, wielding an orb staff (model sheet; was a long sword)
# (storyboard row 5: "クイーン vs ポーン / 剣での斬撃"). exec'd after warriors.py + knight.py (sheet / weigh).
# Standard humanoid rig + "weapon" (bone Y runs along the blade, so aims point the sword).

def build_queen():
    p = {"bulk": 0.88, "leg": 1.04, "head": 0.95, "base": 0.0}
    J = skeleton(p)
    body = skin_body(J, p)
    head(J, face=True)
    hd = J["head"] + Vector((0, 0, 0.1))
    # hair: a smooth fall from the crown to between the shoulders
    shell("Hair", [(0.0, 0.11), (0.08, 0.09), (0.105, 0.02), (0.1, -0.08), (0.11, -0.2), (0.09, -0.28)], M_BODY, "head", 24,
          Matrix.Translation(hd + Vector((0, 0.012, 0))) @ Matrix.Diagonal((0.95, 1.0, 1, 1)), a0=math.radians(10), a1=math.radians(170), thick=0.02)
    # crown: gold circlet with tall fleuron points and gems
    cm = Matrix.Translation(hd + Vector((0, 0, 0.06)))
    lathe("Circlet", [(0.088, 0), (0.1, 0), (0.104, 0.04), (0.092, 0.04)], M_TRIM, "head", 24, cm)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        tall = 0.11 if k % 2 == 0 else 0.07
        base = hd + Vector((0.098 * math.sin(a), -0.098 * math.cos(a), 0.09))
        rod(f"CrownPt{k}", base, base + Vector((0.012 * math.sin(a), -0.012 * math.cos(a), tall)), 0.022, 0.004, M_TRIM, "head", 6)
        sphere(f"CrownGem{k}", 0.012, base + Vector((0.004 * math.sin(a), -0.004 * math.cos(a), tall + 0.004)), M_TRIM, "head", seg=8)
    sphere("BrowJewel", 0.018, hd + Vector((0, -0.104, 0.08)), M_GLOW, "head", seg=10)
    # high standing collar
    weigh(sheet("Collar", lambda u, v: J["neck"] + Vector((0.13 * math.cos(math.pi * (0.1 + 0.8 * u)) * (1 + 0.35 * v),
                                                            0.1 * math.sin(math.pi * (0.1 + 0.8 * u)) * (1 + 0.35 * v) + 0.02,
                                                            -0.03 + 0.2 * v)), 10, 3, M_TRIM, 0.012), lambda co: {"chest": 1.0})
    # bodice
    ch = (J["spine"] + J["chest"]) / 2
    shell("Bodice", [(0.15, -0.17), (0.155, -0.05), (0.18, 0.08), (0.165, 0.19), (0.07, 0.24)], M_BODY, "chest", 32,
          Matrix.Translation(ch) @ Matrix.Diagonal((1, 0.78, 1, 1)), thick=0.014)
    shell("Stomacher", [(0.162, -0.15), (0.17, 0.05), (0.16, 0.16)], M_TRIM, "chest", 16,
          Matrix.Translation(ch + Vector((0, -0.006, 0))) @ Matrix.Diagonal((1, 0.78, 1, 1)), a0=math.radians(250), a1=math.radians(290), thick=0.008)
    # gown: full bell skirt to the floor with gold hem and a front panel
    top = J["spine"] - Vector((0, 0, 0.02))
    length = top.z - 0.01
    mg = Matrix.Translation(top) @ Matrix.Diagonal((1, 0.9, 1, 1))
    for o in (shell("Gown", [(0.17, 0.0), (0.21, -0.12), (0.3, -0.45), (0.42, -length)], M_BODY, None, 48, mg, thick=0.014),
              shell("GownHem", [(0.422, -length + 0.07), (0.426, -length + 0.005)], M_TRIM, None, 48, mg, thick=0.016),
              shell("GownPanel", [(0.175, -0.02), (0.215, -0.13), (0.305, -0.45), (0.426, -length + 0.01)], M_TRIM, None, 8, mg,
                    a0=math.radians(258), a1=math.radians(282), thick=0.018)):
        skirt_weights(o, top.z, top.z - length, 0.15)
    lathe("Girdle", [(0, -0.025), (0.18, -0.025), (0.185, 0.025), (0, 0.025)], M_TRIM, "spine", 32, mg)
    # train/cape from the shoulders, long and flowing behind
    ctop = (J["shoulder.L"] + J["shoulder.R"]) / 2 + Vector((0, 0.09, 0.02))
    def cape(u, v):
        side = abs(u - 0.5) * 2
        x = (u - 0.5) * (0.44 + 0.5 * v)
        y = 0.3 * v * v + 0.06 * math.sin(u * math.pi * 7) * v + 0.04 * side
        z = -(ctop.z - 0.02) * v
        return ctop + Vector((x, y, z))
    def capew(co):
        t = min(1, max(0, (ctop.z - co.z) / ctop.z))
        side = "L" if co.x > 0 else "R"
        return {"chest": max(0, 1 - 2 * t), "spine": max(0, 1 - abs(t - 0.5) * 2) * 0.6, "hips": max(0, 2 * t - 1) * 0.6,
                f"thigh.{side}": max(0, 2 * t - 1) * 0.4}
    weigh(sheet("Cape", cape, 14, 12, M_BODY, 0.016), capew)
    weigh(sheet("CapeHem", lambda u, v: cape(u, 0.95 + 0.05 * v) + Vector((0, 0.004, 0)), 14, 1, M_TRIM, 0.022), capew)
    # puffed shoulders, fitted sleeves, gold cuffs, slender hands
    for L in ("L", "R"):
        sh, e, w, ht = J[f"shoulder.{L}"], J[f"elbow.{L}"], J[f"wrist.{L}"], J[f"handtip.{L}"]
        sphere(f"Puff{L}", 0.085, sh, M_BODY, f"upper_arm.{L}", scale=(1, 1, 0.9), seg=14)
        rod(f"Sleeve{L}", sh, e, 0.06, 0.05, M_BODY, f"upper_arm.{L}", 12)
        rod(f"Forearm{L}", e, w, 0.05, 0.042, M_BODY, f"forearm.{L}", 12)
        rod(f"Cuff{L}", w - (w - e) * 0.12, w, 0.05, 0.058, M_TRIM, f"forearm.{L}", 12)
        if L == "R": fist(J, L, 0.7, 0.022, 0.85)   # the staff hand
        else: sphere(f"Hand{L}", 0.042, w + (ht - w) * 0.7, M_BODY, f"hand.{L}", scale=(0.85, 1, 1.1), seg=12)
    for L in ("L", "R"):
        t, f = J[f"ankle.{L}"], J[f"toe.{L}"]
        box(f"Shoe{L}", (0.08, 0.22, 0.06), (t.x, (t.y + f.y) / 2 - 0.03, t.z - 0.05), M_BODY, f"foot.{L}", bevel=0.025, taper=(0.7, 0.6))
    # model sheet: a tall gold-banded staff crowned by an orb in a cage of gold bands, held in the right fist;
    # the weapon bone runs up the staff toward the orb, which is the striking end in the queen's attacks
    w, t = J["wrist.R"], J["handtip.R"]
    g = w + (t - w) * 0.7
    Z = Vector((0, 0, 1))
    lo, hi = g - Z * 0.45, g + Z * 0.95
    rod("QStaff", lo, hi, 0.022, 0.019, M_BODY, "weapon", 12)
    rod("QStaffFoot", lo - Z * 0.03, lo + Z * 0.05, 0.018, 0.028, M_TRIM, "weapon", 10)
    for k, z in enumerate((0.25, 0.6, 0.9)):
        rod(f"QStaffBand{k}", g + Z * (z - 0.015), g + Z * (z + 0.015), 0.03, 0.03, M_TRIM, "weapon", 10)
    oc = hi + Z * 0.1
    sphere("QOrb", 0.055, oc, M_GLOW, "weapon", seg=16)
    for k in range(3):   # the cage: three gold bands around the orb
        a0 = k / 3 * math.pi
        pts = [oc + Vector((0.08 * math.cos(a0) * math.sin(u / 16 * 2 * math.pi), 0.08 * math.sin(a0) * math.sin(u / 16 * 2 * math.pi),
                            0.08 * math.cos(u / 16 * 2 * math.pi))) for u in range(17)]
        for u in range(16):
            rod(f"QCage{k}_{u}", pts[u], pts[u + 1], 0.008, 0.008, M_TRIM, "weapon", 6)
    sphere("QFinial", 0.02, oc + Z * 0.1, M_TRIM, "weapon", seg=8)
    rod("QCollar", hi - Z * 0.02, oc - Z * 0.07, 0.03, 0.02, M_TRIM, "weapon", 10)
    extra = {"weapon": (g, g + Z * 0.4, "hand.R")}   # bone Y up the staff, toward the orb
    return J, body, extra, 0.85   # taller than the pawn: ~1.6 squares with the crown

PIECES["Queen"] = build_queen
