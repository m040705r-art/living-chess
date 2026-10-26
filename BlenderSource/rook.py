# Rook (model sheet, 2026-10-25): an armoured knight whose great helm is a castle tower - battlements for a
# crown, a dark vision slit - with a long gold-edged tabard, an arming sword in the right fist and a big kite
# shield with a fleur-de-lis on the left forearm. No pedestal. Standard humanoid rig + "weapon" + "shield".
# The rook still charges and tackles (rook_anims.py): now it leads with the shield.

def tower_helm(J):
    hc = J["head"] + Vector((0, 0, 0.1))
    r = 0.125
    lathe("TowerHelm", [(0, -0.12), (r, -0.12), (r + 0.004, 0.08), (r + 0.02, 0.1), (r + 0.02, 0.13), (0, 0.13)],
          M_BODY, "head", 24, Matrix.Translation(hc))
    lathe("HelmBand", [(r + 0.002, -0.02), (r + 0.012, -0.02), (r + 0.012, 0.01), (r + 0.002, 0.01)], M_TRIM, "head", 24,
          Matrix.Translation(hc))
    for k in range(6):   # crenellations crowning the helm
        a = (k + 0.5) / 6 * 2 * math.pi
        box(f"HelmMerlon{k}", (0.07, 0.05, 0.07), hc + Vector(((r + 0.005) * math.sin(a), -(r + 0.005) * math.cos(a), 0.16)),
            M_BODY, "head", rot=(0, 0, a), bevel=0.008)
    box("HelmSlit", (0.15, 0.03, 0.022), hc + Vector((0, -r - 0.002, 0.0)), M_DARK, "head")
    box("HelmBreaths", (0.012, 0.03, 0.06), hc + Vector((0.045, -r - 0.002, -0.06)), M_DARK, "head")

def build_rook():
    p = {"bulk": 1.15, "leg": 1.0, "head": 1.0, "base": 0.0}
    J = skeleton(p)
    body = skin_body(J, p)
    head(J, face=False)
    tower_helm(J)
    cuirass(J, 1.15); pauldrons(J, 0.12)
    surcoat(J, 0.72, 1.15)
    limb_armour(J, grip=("L", "R"))
    g = sword(J, 0.8, "R", "weapon", 1.0, 0.036)
    c = kite_shield(J, 1.75, emblem=False)
    crest(c + Vector((0, 0, 0.02)), 1.75)
    d = Vector((0, -1, 0.15)).normalized()
    fa = J["elbow.L"] + (J["wrist.L"] - J["elbow.L"]) * 0.9
    # a scabbard at the left hip for the iai (sheet "ルーク | 居合モーション"): drawn across the body with the right hand
    scabbard(J, "R", 0.8)
    hilt, dn = sheath_frame(J, "R")
    hl = (J["handtip.R"] - J["wrist.R"]).length * 0.7
    to_sh = J["shoulder.R"] - hilt; to_sh.z = 0; to_sh.normalize()
    wr = hilt + to_sh * hl * 0.85 + Vector((0, 0.03, hl * 0.4))
    extra = {"weapon": (g, g + d * 0.3, "hand.R"),
             "shield": (fa, fa + Vector((0, 0, 0.25)), "forearm.L"),   # pivot on the forearm; Y = up, Z = face
             "sheath.R": (hilt, hilt + dn * 0.2, "hips"), "hilt.R": (wr, wr + Vector((0, 0, 0.08)), "hips")}
    return J, body, extra, 0.7   # ~1.3 squares: a big man in a tall helm

PIECES["Rook"] = build_rook
