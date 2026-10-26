# King: a bearded warrior-king under an arched crown topped by a cross, in a long royal robe and mantle,
# with sword and kite shield (model sheet 2026-10-25; was a two-handed greatsword).
# exec'd after warriors.py + knight.py (sheet / weigh). Standard humanoid rig + "weapon" (Y along the blade).

def stiffen(ob, k):
    """Move part of the thigh weight back to the hips (the robe follows the legs less)."""
    vg = {g.name: g for g in ob.vertex_groups}
    for v in ob.data.vertices:
        w = {ob.vertex_groups[g.group].name: g.weight for g in v.groups}
        moved = (w.get("thigh.L", 0) + w.get("thigh.R", 0)) * (1 - k)
        for n in ("thigh.L", "thigh.R"):
            vg[n].add([v.index], w.get(n, 0) * k, 'REPLACE')
        vg["hips"].add([v.index], w.get("hips", 0) + moved, 'REPLACE')

def build_king():
    p = {"bulk": 1.1, "leg": 1.0, "head": 1.0, "base": 0.0}
    J = skeleton(p)
    body = skin_body(J, p)
    head(J, beard=True, face=True)
    hd = J["head"] + Vector((0, 0, 0.1))
    # full forked beard and moustache
    sphere("BeardLong", 0.07, hd + Vector((0, -0.06, -0.14)), M_BODY, "head", scale=(1.0, 0.7, 1.4), seg=14)
    for s in (1, -1):
        rod(f"Moustache{s}", hd + Vector((0, -0.1, -0.03)), hd + Vector((s * 0.06, -0.085, -0.06)), 0.014, 0.006, M_BODY, "head", 6)
    # crown: gold circlet with fleurons, four arches meeting under an orb and a cross
    cm = Matrix.Translation(hd + Vector((0, 0, 0.055)))
    lathe("Circlet", [(0.098, 0), (0.112, 0), (0.116, 0.05), (0.102, 0.05)], M_TRIM, "head", 24, cm)
    top = hd + Vector((0, 0, 0.2))
    for k in range(4):
        a = k / 4 * 2 * math.pi + math.pi / 4
        pts = [hd + Vector((0.11 * math.sin(a) * math.cos(t), -0.11 * math.cos(a) * math.cos(t), 0.1 + 0.1 * math.sin(t)))
               for t in (0, 0.5, 1.0, math.pi / 2)]
        for i in range(3):
            rod(f"Arch{k}_{i}", pts[i], pts[i + 1], 0.012, 0.012, M_TRIM, "head", 6)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        b = hd + Vector((0.11 * math.sin(a), -0.11 * math.cos(a), 0.1))
        rod(f"Fleuron{k}", b, b + Vector((0.01 * math.sin(a), -0.01 * math.cos(a), 0.05 if k % 2 else 0.035)), 0.018, 0.004, M_TRIM, "head", 6)
    sphere("CrownCap", 0.085, hd + Vector((0, 0, 0.12)), M_BODY, "head", scale=(1, 1, 0.75), seg=14)   # velvet cap inside the arches
    sphere("CrownOrb", 0.026, top + Vector((0, 0, 0.01)), M_TRIM, "head", seg=10)
    box("CrossV", (0.022, 0.022, 0.1), top + Vector((0, 0, 0.08)), M_TRIM, "head", bevel=0.004)
    box("CrossH", (0.07, 0.022, 0.022), top + Vector((0, 0, 0.095)), M_TRIM, "head", bevel=0.004)
    sphere("CrownGem", 0.016, hd + Vector((0, -0.116, 0.08)), M_GLOW, "head", seg=8)
    # armour under the robes
    cuirass(J, 1.1); pauldrons(J, 0.12)
    ch = (J["spine"] + J["chest"]) / 2
    rod("Chain", ch + Vector((-0.12, -0.17, 0.14)), ch + Vector((0, -0.2, 0.0)), 0.01, 0.01, M_TRIM, "chest", 6)
    rod("Chain2", ch + Vector((0.12, -0.17, 0.14)), ch + Vector((0, -0.2, 0.0)), 0.01, 0.01, M_TRIM, "chest", 6)
    sphere("Pendant", 0.03, ch + Vector((0, -0.205, -0.02)), M_TRIM, "chest", scale=(1, 0.5, 1.2), seg=10)
    # long royal robe to the floor: gold hem and a gold front panel
    tp = J["spine"] - Vector((0, 0, 0.02))
    length = tp.z - 0.01
    mg = Matrix.Translation(tp) @ Matrix.Diagonal((1, 0.88, 1, 1))
    for o in (shell("Robe", [(0.2, 0.0), (0.23, -0.12), (0.29, -0.45), (0.37, -length)], M_BODY, None, 48, mg, thick=0.016),
              shell("RobeHem", [(0.372, -length + 0.08), (0.376, -length + 0.005)], M_TRIM, None, 48, mg, thick=0.018),
              shell("RobePanel", [(0.205, -0.02), (0.235, -0.13), (0.295, -0.45), (0.376, -length + 0.01)], M_TRIM, None, 8, mg,
                    a0=math.radians(256), a1=math.radians(284), thick=0.02)):
        skirt_weights(o, tp.z, tp.z - length, 0.17)
        stiffen(o, 0.45)   # a heavy robe: the hem swung under the board when the back leg drove the cleave
    lathe("Belt", [(0, -0.03), (0.215, -0.03), (0.22, 0.03), (0, 0.03)], M_TRIM, "spine", 32, mg)
    box("Buckle", (0.07, 0.02, 0.07), tp + Vector((0, -0.195, 0)), M_TRIM, "spine", bevel=0.01)
    # ermine mantle round the shoulders (rolled collar) and a long cape behind
    nk = J["neck"]
    shell("Mantle", [(0.12, 0.04), (0.2, 0.0), (0.27, -0.06), (0.3, -0.13)], M_BODY, "chest", 32,
          Matrix.Translation(nk - Vector((0, 0, 0.02))) @ Matrix.Diagonal((1, 0.85, 1, 1)), thick=0.03)
    shell("MantleEdge", [(0.298, -0.12), (0.305, -0.16)], M_TRIM, "chest", 32,
          Matrix.Translation(nk - Vector((0, 0, 0.02))) @ Matrix.Diagonal((1, 0.85, 1, 1)), thick=0.02)
    ctop = (J["shoulder.L"] + J["shoulder.R"]) / 2 + Vector((0, 0.1, 0.0))
    def cape(u, v):
        side = abs(u - 0.5) * 2
        x = (u - 0.5) * (0.5 + 0.45 * v)
        y = 0.22 * v * v + 0.05 * math.sin(u * math.pi * 6) * v + 0.05 * side
        z = -(ctop.z - 0.02) * v
        return ctop + Vector((x, y, z))
    def capew(co):
        t = min(1, max(0, (ctop.z - co.z) / ctop.z))
        side = "L" if co.x > 0 else "R"
        return {"chest": max(0, 1 - 2 * t), "spine": max(0, 1 - abs(t - 0.5) * 2) * 0.6, "hips": max(0, 2 * t - 1) * 0.6,
                f"thigh.{side}": max(0, 2 * t - 1) * 0.4}
    weigh(sheet("Cape", cape, 14, 12, M_BODY, 0.018), capew)
    weigh(sheet("CapeHem", lambda u, v: cape(u, 0.95 + 0.05 * v) + Vector((0, 0.004, 0)), 14, 1, M_TRIM, 0.024), capew)
    # armoured arms with gold-cuffed gauntlets
    for L in ("L", "R"):
        sh, e, w, ht = J[f"shoulder.{L}"], J[f"elbow.{L}"], J[f"wrist.{L}"], J[f"handtip.{L}"]
        rod(f"Sleeve{L}", sh, e, 0.075, 0.065, M_BODY, f"upper_arm.{L}", 12)
        sphere(f"Elbow{L}", 0.065, e, M_BODY, f"forearm.{L}", seg=12)
        rod(f"Vambrace{L}", e, w, 0.062, 0.055, M_BODY, f"forearm.{L}", 12)
        rod(f"Cuff{L}", w - (w - e) * 0.25, w, 0.06, 0.075, M_TRIM, f"forearm.{L}", 12)
        fist(J, L, 0.7, 0.016, 1.0)   # sword hand / shield-strap hand
    for L in ("L", "R"):
        t, f = J[f"ankle.{L}"], J[f"toe.{L}"]
        box(f"Shoe{L}", (0.1, 0.24, 0.07), (t.x, (t.y + f.y) / 2 - 0.03, t.z - 0.05), M_BODY, f"foot.{L}", bevel=0.03, taper=(0.7, 0.6))
    # model sheet: a long arming sword in the right fist, a great kite shield with the fleur-de-lis on the left forearm
    g = sword(J, 0.95, "R", "weapon", 1.1, 0.04)
    d = Vector((0, -1, 0.15)).normalized()
    c = kite_shield(J, 1.8, emblem=False)
    crest(c + Vector((0, 0, 0.02)), 1.8)
    fa = J["elbow.L"] + (J["wrist.L"] - J["elbow.L"]) * 0.9
    extra = {"weapon": (g, g + d * 0.4, "hand.R"),   # bone Y along the blade
             "shield": (fa, fa + Vector((0, 0, 0.25)), "forearm.L")}
    return J, body, extra, 0.9   # the tallest piece: ~1.8 squares to the cross

PIECES["King"] = build_king
