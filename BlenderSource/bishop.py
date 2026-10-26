# Bishop: a robed battle-priest with a tall mitre and a crozier whose orb throws lightning
# (storyboard row 3: "ビショップ vs ポーン / 魔法攻撃"). exec'd after warriors.py + knight.py (uses sheet / weigh).
# Standard humanoid rig + "weapon" (crozier shaft, Y up the staff) + "orb" (the glowing focus at the crook;
# the viewer / Unity fire the bolt from this bone).

def build_bishop():
    p = {"bulk": 0.95, "leg": 1.0, "head": 1.0, "base": 0.0}
    J = skeleton(p)
    body = skin_body(J, p)
    head(J, beard=True, face=True)
    hd = J["head"] + Vector((0, 0, 0.1))

    # mitre: tall, peaked front and back, gold orphrey bands and a small cross; lappets hang behind
    m = Matrix.Translation(hd + Vector((0, 0, 0.05))) @ Matrix.Diagonal((0.85, 1.0, 1, 1))
    lathe("Mitre", [(0, 0), (0.118, 0), (0.125, 0.07), (0.11, 0.18), (0.075, 0.28), (0.03, 0.35), (0, 0.37)], M_BODY, "head", 24, m)
    lathe("MitreBand", [(0, -0.005), (0.122, -0.005), (0.126, 0.035), (0, 0.035)], M_TRIM, "head", 24, m)
    box("MitreStripe", (0.03, 0.22, 0.3), hd + Vector((0, 0, 0.21)), M_TRIM, "head", bevel=0.006,
        taper=(0.5, 0.35))
    c = hd + Vector((0, -0.075, 0.24))
    box("MitreCrossV", (0.022, 0.012, 0.09), c, M_TRIM, "head", bevel=0.004)
    box("MitreCrossH", (0.06, 0.012, 0.02), c + Vector((0, 0, 0.015)), M_TRIM, "head", bevel=0.004)
    for s in (1, -1):
        box(f"Lappet{s}", (0.04, 0.012, 0.22), hd + Vector((s * 0.05, 0.1, -0.1)), M_TRIM, "neck", rot=(0.15, 0, 0), bevel=0.004)

    # robe: fitted over the chest, falling to the floor, flared; the skirt follows the legs
    ch = (J["spine"] + J["chest"]) / 2
    shell("RobeTop", [(0.19, -0.17), (0.2, -0.05), (0.215, 0.08), (0.18, 0.2), (0.07, 0.25)], M_BODY, "chest", 32,
          Matrix.Translation(ch) @ Matrix.Diagonal((1, 0.75, 1, 1)), thick=0.014)
    top = J["spine"] - Vector((0, 0, 0.02))
    length = top.z - 0.02
    mr = Matrix.Translation(top) @ Matrix.Diagonal((1, 0.82, 1, 1))
    for o in (shell("Robe", [(0.2, 0.0), (0.22, -0.2), (0.27, -0.5), (0.34, -length)], M_BODY, None, 40, mr, thick=0.014),
              shell("RobeHem", [(0.342, -length + 0.06), (0.346, -length + 0.005)], M_TRIM, None, 40, mr, thick=0.016)):
        skirt_weights(o, top.z, top.z - length, 0.16)
    lathe("Cincture", [(0, -0.025), (0.205, -0.025), (0.21, 0.025), (0, 0.025)], M_TRIM, "spine", 32, mr)
    # stole: two gold bands from the shoulders down the front of the robe
    prof = [(0.2, 0.0), (0.22, -0.2), (0.27, -0.5), (0.34, -length)]   # the Robe's profile (radius, drop)
    def robe_front(x, z):
        """y of the robe's front surface at (x, z): the bands lie ON the robe (they hung up to 9 cm in front of it)."""
        d, r = z - top.z, prof[0][0]
        for (r0, d0), (r1, d1) in zip(prof, prof[1:]) if d < 0 else ():
            if d1 <= d <= d0 or (r1, d1) == prof[-1]:
                t = 0 if d0 == d1 else min(1, max(0, (d - d0) / (d1 - d0))); r = r0 + (r1 - r0) * t; break
        return -0.82 * math.sqrt(max(1e-6, r * r - x * x)) - 0.016   # outside the shell's thickness
    for s in (1, -1):
        a = J[f"shoulder.{'L' if s > 0 else 'R'}"] + Vector((-s * 0.09, -0.12, 0.0))
        z0 = top.z - 0.05
        rod(f"StoleUp{s}", a, Vector((s * 0.07, robe_front(s * 0.07, z0 + 0.07), top.z + 0.02)), 0.022, 0.022, M_TRIM, "chest", 6)
        def stole(u, v, s=s):
            x, z = s * 0.07 + (u - 0.5) * 0.07, z0 - 0.72 * v
            return Vector((x, robe_front(x, z), z))
        weigh(sheet(f"Stole{s}", stole, 1, 8, M_TRIM, 0.012),
              lambda co, s=s: {"hips": 0.5, f"thigh.{'L' if s > 0 else 'R'}": 0.5})
    # cope: a long mantle from the shoulders to the floor, clasped at the chest
    ctop = (J["shoulder.L"] + J["shoulder.R"]) / 2 + Vector((0, 0.1, 0.03))
    def cope(u, v):
        side = abs(u - 0.5) * 2
        x = (u - 0.5) * (0.48 + 0.34 * v)
        y = 0.12 * v + 0.05 * math.sin(u * math.pi * 6) * v + 0.06 * side * (1 - v)
        z = -(ctop.z - 0.04) * v
        return ctop + Vector((x, y, z))
    def copew(co):
        t = min(1, max(0, (ctop.z - co.z) / ctop.z))
        side = "L" if co.x > 0 else "R"
        return {"chest": max(0, 1 - 2 * t), "spine": max(0, 1 - abs(t - 0.5) * 2) * 0.6, "hips": max(0, 2 * t - 1) * 0.6,
                f"thigh.{side}": max(0, 2 * t - 1) * 0.4}
    weigh(sheet("Cope", cope, 12, 12, M_BODY, 0.016), copew)
    weigh(sheet("CopeHem", lambda u, v: cope(u, 0.95 + 0.05 * v) + Vector((0, 0.004, 0)), 12, 1, M_TRIM, 0.022), copew)
    weigh(sheet("CopeCollar", lambda u, v: ctop + Vector(((u - 0.5) * 0.5, -0.02 + 0.02 * v, 0.06 - 0.08 * v)), 8, 1, M_TRIM, 0.02),
          lambda co: {"chest": 1.0})
    sphere("Morse", 0.04, J["chest"] + Vector((0, -0.17, 0.12)), M_TRIM, "chest", scale=(1, 0.5, 1))
    # wide bell sleeves, gold cuffs; bare hands
    for L in ("L", "R"):
        e, w, ht = J[f"elbow.{L}"], J[f"wrist.{L}"], J[f"handtip.{L}"]
        sh = J[f"shoulder.{L}"]
        rod(f"SleeveUp{L}", sh, e, 0.075, 0.08, M_BODY, f"upper_arm.{L}", 14)
        rod(f"Sleeve{L}", e, w + (w - e) * 0.05, 0.08, 0.13, M_BODY, f"forearm.{L}", 16)
        rod(f"Cuff{L}", w - (w - e) * 0.08, w + (w - e) * 0.06, 0.135, 0.14, M_TRIM, f"forearm.{L}", 16)
        if L == "R": fist(J, L, 0.75, 0.027, 0.95)   # around the crozier
        else: sphere(f"Hand{L}", 0.05, w + (ht - w) * 0.7, M_BODY, f"hand.{L}", scale=(0.85, 1, 1.1), seg=12)
    for L in ("L", "R"):   # slippers peeking from the hem
        t, f = J[f"ankle.{L}"], J[f"toe.{L}"]
        box(f"Slipper{L}", (0.1, 0.24, 0.07), (t.x, (t.y + f.y) / 2 - 0.03, t.z - 0.05), M_BODY, f"foot.{L}", bevel=0.03, taper=(0.8, 0.7))

    # staff in the right hand, gold knop, wheel head around a glowing orb (model sheet)
    w, t = J["wrist.R"], J["handtip.R"]
    g = w + (t - w) * 0.75
    Z = Vector((0, 0, 1)); L = 2.0
    lo, hi = g - Z * (L * 0.5), g + Z * (L * 0.5)
    rod("Staff", lo, hi, 0.028, 0.024, M_BODY, "weapon", 12)
    rod("StaffFoot", lo - Z * 0.03, lo + Z * 0.06, 0.02, 0.032, M_TRIM, "weapon", 12)
    for k, z in enumerate((0.3, 0.7)):
        rod(f"StaffRing{k}", lo + Z * (L * z - 0.02), lo + Z * (L * z + 0.02), 0.036, 0.036, M_TRIM, "weapon", 12)
    sphere("Knop", 0.06, hi - Z * 0.02, M_TRIM, "weapon", scale=(1, 1, 0.8), seg=14)
    # model sheet: the staff ends in a gold wheel - a rim with eight spokes and studs - around a glowing orb
    c = hi + Z * 0.2
    R0 = 0.16
    rim = [c + Vector((R0 * math.sin(k / 24 * 2 * math.pi), 0, R0 * math.cos(k / 24 * 2 * math.pi))) for k in range(25)]
    for k in range(24):
        rod(f"WheelRim{k}", rim[k], rim[k + 1], 0.018, 0.018, M_TRIM, "weapon", 8)
    for k in range(8):
        a = k / 8 * 2 * math.pi; u = Vector((math.sin(a), 0, math.cos(a)))
        rod(f"WheelSpoke{k}", c + u * 0.07, c + u * R0, 0.009, 0.009, M_TRIM, "weapon", 6)
        sphere(f"WheelStud{k}", 0.022, c + u * (R0 + 0.025), M_TRIM, "weapon", seg=8)
    rod("WheelNeck", hi, c - Z * R0, 0.026, 0.02, M_TRIM, "weapon", 10)
    orb = c
    sphere("Orb", 0.065, orb, M_GLOW, "weapon", seg=16)

    extra = {"weapon": (g, g + Vector((0, 0, 0.4)), "hand.R"),
             "orb": (orb, orb + Vector((0, 0, 0.1)), "weapon")}
    return J, body, extra, 0.64   # a little taller than the pawn

PIECES["Bishop"] = build_bishop
