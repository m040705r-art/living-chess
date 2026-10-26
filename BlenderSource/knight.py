# Knight: a stone knight on a stone warhorse (storyboard row 2: "ナイト vs ポーン / 騎馬での突進").
# exec'd after warriors.py (shares its mesh helpers, materials, humanoid skeleton and armour kit).
# One armature: horse bones are prefixed h_, the rider uses the standard humanoid names so anims.py's
# ARMS / aim helpers work unchanged; the rider's hips hang off the horse's back (h_hips).
# Human scale (rider 1.8 m), facing -Y, then scaled so the horse fits one square nose-to-tail.

HORSE_J = {
    "h_rump": (0, 0.62, 1.18), "h_hip": (0, 0.45, 1.19), "h_back": (0, 0.05, 1.2), "h_chest": (0, -0.42, 1.16),
    "h_breast": (0, -0.56, 1.02), "h_neckb": (0, -0.6, 1.32), "h_neckm": (0, -0.76, 1.56), "h_poll": (0, -0.88, 1.8),
    "h_muzzle": (0, -1.18, 1.52), "h_tailr": (0, 0.7, 1.22), "h_tailm": (0, 0.78, 0.98), "h_taile": (0, 0.8, 0.62),
}
for _s, _L in ((1, "L"), (-1, "R")):
    HORSE_J.update({
        f"h_sh.{_L}": (_s * 0.15, -0.46, 1.02), f"h_el.{_L}": (_s * 0.15, -0.42, 0.75), f"h_kn.{_L}": (_s * 0.14, -0.46, 0.42),
        f"h_fe.{_L}": (_s * 0.14, -0.46, 0.13), f"h_ho.{_L}": (_s * 0.14, -0.52, 0.0),
        f"h_hp.{_L}": (_s * 0.15, 0.48, 1.05), f"h_st.{_L}": (_s * 0.17, 0.36, 0.72), f"h_hk.{_L}": (_s * 0.14, 0.62, 0.45),
        f"h_hf.{_L}": (_s * 0.14, 0.58, 0.13), f"h_hh.{_L}": (_s * 0.14, 0.55, 0.0),
    })

HORSE_BONES = [
    ("h_hips", "h_hip", "h_back", "root"), ("h_chest", "h_back", "h_chest", "h_hips"),
    ("h_neck1", "h_neckb", "h_neckm", "h_chest"), ("h_neck2", "h_neckm", "h_poll", "h_neck1"),
    ("h_head", "h_poll", "h_muzzle", "h_neck2"),
    ("h_tail1", "h_tailr", "h_tailm", "h_hips"), ("h_tail2", "h_tailm", "h_taile", "h_tail1"),
]
for _L in ("L", "R"):
    HORSE_BONES += [
        (f"h_fupper.{_L}", f"h_sh.{_L}", f"h_el.{_L}", "h_chest"), (f"h_fore.{_L}", f"h_el.{_L}", f"h_kn.{_L}", f"h_fupper.{_L}"),
        (f"h_fcannon.{_L}", f"h_kn.{_L}", f"h_fe.{_L}", f"h_fore.{_L}"), (f"h_fhoof.{_L}", f"h_fe.{_L}", f"h_ho.{_L}", f"h_fcannon.{_L}"),
        (f"h_thigh.{_L}", f"h_hp.{_L}", f"h_st.{_L}", "h_hips"), (f"h_gaskin.{_L}", f"h_st.{_L}", f"h_hk.{_L}", f"h_thigh.{_L}"),
        (f"h_hcannon.{_L}", f"h_hk.{_L}", f"h_hf.{_L}", f"h_gaskin.{_L}"), (f"h_hhoof.{_L}", f"h_hf.{_L}", f"h_hh.{_L}", f"h_hcannon.{_L}"),
    ]

RIDER_SEAT = Vector((0, 0.02, 0.7))   # standing-skeleton offset that puts the rider's pelvis on the saddle

def rider_skeleton(p):
    J = skeleton(p)
    for k in list(J):
        if k != "root": J[k] = J[k] + RIDER_SEAT
    for s, L in ((1, "L"), (-1, "R")):   # legs astride the barrel
        J[f"hip.{L}"] = Vector((s * 0.11, 0.02, 1.62))
        J[f"knee.{L}"] = Vector((s * 0.36, -0.2, 1.3))
        J[f"ankle.{L}"] = Vector((s * 0.36, -0.08, 0.95))
        J[f"toe.{L}"] = Vector((s * 0.36, -0.22, 0.92))
    return J

def horse_skin(J):
    nodes = [("h_rump", 0.26, 0.27), ("h_hip", 0.31, 0.33), ("h_back", 0.3, 0.34), ("h_chest", 0.3, 0.36)]   # heavy warhorse
    edges = [(0, 1), (1, 2), (2, 3)]
    def add(n, rx, ry, link):
        nodes.append((n, rx, ry)); edges.append((link, len(nodes) - 1)); return len(nodes) - 1
    add("h_breast", 0.23, 0.24, 3)
    i = add("h_neckb", 0.21, 0.25, 3); i = add("h_neckm", 0.16, 0.2, i); i = add("h_poll", 0.1, 0.12, i)
    add("h_muzzle", 0.075, 0.09, i)
    for L in ("L", "R"):   # only the muscular tops of the legs are skinned; the rest are carved segments
        i = add(f"h_sh.{L}", 0.15, 0.16, 3); add(f"h_el.{L}", 0.11, 0.11, i)
        i = add(f"h_hp.{L}", 0.18, 0.19, 1); add(f"h_st.{L}", 0.13, 0.13, i)
    me = bpy.data.meshes.new("Horse")
    me.from_pydata([tuple(J[n]) for n, _, _ in nodes], edges, [])
    ob = bpy.data.objects.new("Horse", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.modifiers.new("Skin", 'SKIN')
    for k, (_, rx, ry) in enumerate(nodes):
        me.skin_vertices[0].data[k].radius = (rx, ry)
    me.skin_vertices[0].data[0].use_root = True
    ob.modifiers.new("Sub", 'SUBSURF').levels = 2
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear(); ob.data = me2; bpy.data.meshes.remove(me)
    me2.materials.append(M_BODY)
    return ob

def horse_details(J):
    poll, muz = J["h_poll"], J["h_muzzle"]
    # ears, eyes, nostrils, forelock
    for s in (1, -1):
        rod(f"Ear{s}", poll + Vector((s * 0.05, 0.03, 0.02)), poll + Vector((s * 0.07, 0.06, 0.16)), 0.03, 0.006, M_BODY, "h_head", 8)
        sphere(f"Nostril{s}", 0.018, muz + Vector((s * 0.032, -0.025, -0.01)), M_DARK, "h_head", seg=6)   # set into the muzzle
    # armoured chanfron down the face, bridle bands
    d = (muz - poll).normalized()
    box("Chanfron", (0.1, 0.03, (muz - poll).length * 0.8), poll + (muz - poll) * 0.45 + Vector((0, -0.07, 0.04)),
        M_TRIM, "h_head", rot=(math.atan2(d.y, d.z) * -1 + math.pi, 0, 0), bevel=0.01)
    for t in (0.25, 0.8):
        c = poll + (muz - poll) * t
        lathe(f"Bridle{t}", [(0, -0.012), (0.1 - t * 0.04, -0.012), (0.1 - t * 0.04, 0.012), (0, 0.012)], M_TRIM, "h_head", 16,
              along(c, c + d) @ Matrix.Diagonal((1.0, 1.15, 1, 1)))
    # mane: a row of carved locks along the crest, split between the neck bones
    n0, n1 = J["h_neckb"] + Vector((0, 0.1, 0.12)), poll + Vector((0, 0.08, 0.05))
    for k in range(9):
        t = k / 8; c = n0 + (n1 - n0) * t
        box(f"Mane{k}", (0.05, 0.1, 0.14), c, M_BODY, "h_neck2" if t > 0.5 else "h_neck1",
            rot=(math.radians(-35), 0, 0), bevel=0.012)
    # tail: tapered locks on the two tail bones
    for k, (a, b, bone) in enumerate(((J["h_tailr"], J["h_tailm"], "h_tail1"), (J["h_tailm"], J["h_taile"], "h_tail2"))):
        rod(f"Tail{k}", a, b, 0.09 - k * 0.01, 0.08 - k * 0.04, M_BODY, bone, 12)
    # lower legs: carved segments with knobbly joints, each rigid on its bone (reads clearly at board scale)
    for L in ("L", "R"):
        for seg, (a, b, bone, r0, r1) in enumerate((
                (f"h_el.{L}", f"h_kn.{L}", f"h_fore.{L}", 0.085, 0.06), (f"h_kn.{L}", f"h_fe.{L}", f"h_fcannon.{L}", 0.05, 0.045),
                (f"h_st.{L}", f"h_hk.{L}", f"h_gaskin.{L}", 0.1, 0.06), (f"h_hk.{L}", f"h_hf.{L}", f"h_hcannon.{L}", 0.05, 0.045))):
            rod(f"Leg{L}{seg}", J[a], J[b], r0, r1, M_BODY, bone, 12)
        for jn, bone, r in ((f"h_kn.{L}", f"h_fcannon.{L}", 0.065), (f"h_fe.{L}", f"h_fhoof.{L}", 0.055),
                            (f"h_hk.{L}", f"h_hcannon.{L}", 0.07), (f"h_hf.{L}", f"h_hhoof.{L}", 0.055)):
            sphere(f"Joint{jn}", r, J[jn], M_BODY, bone, seg=12)
    # hooves
    for L in ("L", "R"):
        for hoof, fet, bone in ((f"h_ho.{L}", f"h_fe.{L}", f"h_fhoof.{L}"), (f"h_hh.{L}", f"h_hf.{L}", f"h_hhoof.{L}")):
            h = J[hoof]; f = J[fet]
            rod(f"Hoof{hoof}", Vector((f.x, (h.y + f.y) / 2, 0.0)), Vector((f.x, f.y, 0.12)), 0.09, 0.07, M_BODY, bone, 14)
    # saddle with pommel and cantle, saddle cloth over the back
    box("SaddleCloth", (0.7, 0.62, 0.04), Vector((0, 0.06, 1.53)), M_TRIM, "h_hips", bevel=0.015)
    box("Saddle", (0.38, 0.46, 0.07), Vector((0, 0.04, 1.57)), M_BODY, "h_hips", bevel=0.025)
    box("Pommel", (0.18, 0.06, 0.12), Vector((0, -0.18, 1.63)), M_BODY, "h_hips", bevel=0.02)
    box("Cantle", (0.3, 0.06, 0.14), Vector((0, 0.26, 1.64)), M_BODY, "h_hips", bevel=0.02)

def lance(J, L=2.4, hand="R"):
    """Jousting lance held near its butt: weapon bone runs up the shaft (Y) like the pawn's spear."""
    w, t = J[f"wrist.{hand}"], J[f"handtip.{hand}"]
    g = w + (t - w) * 0.75
    Z = Vector((0, 0, 1))
    lo, hi = g - Z * (L * 0.18), g + Z * (L * 0.82)
    rod("LanceButt", lo, g - Z * 0.08, 0.045, 0.05, M_BODY, "weapon", 12)
    rod("LanceGrip", g - Z * 0.08, g + Z * 0.1, 0.035, 0.035, M_TRIM, "weapon", 12)
    rod("Vamplate", g + Z * 0.1, g + Z * 0.36, 0.13, 0.04, M_TRIM, "weapon", 16)   # hand guard cone
    rod("LanceShaft", g + Z * 0.36, hi, 0.045, 0.022, M_BODY, "weapon", 12)
    rod("TipCollar", hi - Z * 0.03, hi + Z * 0.08, 0.04, 0.05, M_TRIM, "weapon", 12)
    bm = lathe_bm([(0, 0), (0.07, 0.07), (0.05, 0.16), (0.075, 0.2), (0.03, 0.3), (0, 0.42)], 4)   # winged leaf blade
    xform(bm, Matrix.Translation(hi + Z * 0.08) @ Matrix.Rotation(math.pi / 4, 4, 'Z') @ Matrix.Diagonal((1, 0.22, 1, 1)))
    new_obj(bm, "LanceTip", M_TRIM, "weapon")
    return g

# ---------------------------------------------------------------- regalia (design board: plume, cape, caparison,
# gold-trimmed barding, crested shield, ornate spear head)
def sheet(name, fn, nu, nv, material, thick=0.012):
    """Surface from fn(u, v) -> Vector, u, v in 0..1, solidified; returns the object (weights added by weigh())."""
    bm = bmesh.new()
    vs = [[bm.verts.new(fn(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            bm.faces.new([vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]])
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thick)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(bm, name, material, None)

def weigh(ob, fn):
    """fn(co) -> {bone: weight} for every vertex."""
    groups = {}
    for v in ob.data.vertices:
        for b, w in fn(v.co).items():
            if w <= 0: continue
            g = groups.get(b) or ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)
            groups[b] = g
            g.add([v.index], w, 'REPLACE')

def regalia(J):
    hd = J["head"] + Vector((0, 0, 0.1))
    # plume: three feathered ribbons sweeping back from the helmet crest
    for k, (dx, lift) in enumerate(((0.0, 0.03), (0.04, 0.0), (-0.04, 0.0), (0.075, -0.04), (-0.075, -0.04))):
        def f(u, v, dx=dx, lift=lift, k=k):   # arches up off the crest, then cascades down the back
            y = 0.04 + 0.5 * v
            z = 0.22 + lift + 0.28 * math.sin(v * math.pi * 0.8) - 0.5 * v * v
            return hd + Vector((dx * (1 + v) + (u - 0.5) * 0.13 * (1 - 0.5 * v), y, z + 0.035 * math.sin(v * 8 + k * 1.7)))
        weigh(sheet(f"Plume{k}", f, 3, 12, M_BODY, 0.03), lambda co: {"head": 1.0})
    rod("PlumeHolder", hd + Vector((0, 0.04, 0.12)), hd + Vector((0, 0.06, 0.21)), 0.025, 0.03, M_TRIM, "head", 10)
    # cape: hangs from the shoulders and billows back over the horse's rump
    top = (J["shoulder.L"] + J["shoulder.R"]) / 2 + Vector((0, 0.13, 0.02))
    def cape(u, v):
        side = abs(u - 0.5) * 2
        x = (u - 0.5) * (0.4 + 0.28 * v)
        y = 0.6 * v + 0.07 * math.sin(u * math.pi * 5) * v - 0.1 * side * v
        z = -0.55 * v - 0.4 * side * v + 0.05 * math.sin(v * 5 + u * 3) * v
        return top + Vector((x, y, z))
    def capew(co):
        t = min(1, max(0, (co.y - top.y) / 0.75))
        return {"chest": 1.0 - 0.6 * t, "spine": 0.6 * t}
    weigh(sheet("Cape", cape, 10, 10, M_BODY, 0.016), capew)
    weigh(sheet("CapeHem", lambda u, v: cape(u, 0.94 + 0.06 * v) + Vector((0, 0, 0.004)), 10, 1, M_TRIM, 0.02), capew)
    # caparison: a skirt around the barrel, open at the chest for the forelegs, scalloped gold hem
    a0, a1 = math.radians(-60), math.radians(240)   # angle from +X; the gap faces -Y (front)
    def skirt(u, v):
        a = a0 + (a1 - a0) * u
        rx, ry = 0.37 + 0.1 * v, 0.62 + 0.08 * v
        wave = 0.05 * v * math.sin(a * 11)                       # deep vertical folds
        hem = 0.06 * v * abs(math.sin(a * 11))                    # scalloped, uneven hem
        return Vector(((rx + wave) * math.cos(a), 0.08 + (ry + wave) * math.sin(a), 1.5 - 0.74 * v + hem))
    def capw(co):
        t = min(1, max(0, (co.y + 0.3) / 0.6))   # front of the skirt follows the chest, back follows the hips
        return {"h_chest": 1 - t, "h_hips": t}
    weigh(sheet("Caparison", skirt, 40, 6, M_BODY, 0.014), capw)
    weigh(sheet("CaparisonHem", lambda u, v: skirt(u, 0.95 + 0.05 * v) + Vector((0, 0, -0.005)), 40, 1, M_TRIM, 0.022), capw)
    for k in range(7):   # gold fleurons along the cloth
        a = a0 + (a1 - a0) * (k + 0.5) / 7
        c = skirt((k + 0.5) / 7, 0.5)
        sphere(f"Fleuron{k}", 0.035, c + Vector((math.cos(a) * 0.02, math.sin(a) * 0.02, 0)), M_TRIM, None, scale=(0.5, 0.5, 1))
        weigh(PARTS[-1], capw)
    # peytral (breastplate) and crinet (neck plates)
    ch = J["h_breast"] + Vector((0, 0.08, 0.1))
    m = Matrix.Translation(ch) @ Matrix.Diagonal((1, 0.8, 1, 1))
    shell("Peytral", [(0.27, 0.06), (0.3, -0.06), (0.29, -0.14)], M_BODY, "h_chest", 24, m,
          a0=math.radians(200), a1=math.radians(340), thick=0.02)
    shell("PeytralEdge", [(0.3, -0.13), (0.295, -0.16)], M_TRIM, "h_chest", 24, m,
          a0=math.radians(200), a1=math.radians(340), thick=0.03)
    for k in range(4):
        t = (k + 0.5) / 4
        a, b = J["h_neckb"], J["h_poll"]
        c = a + (b - a) * t + Vector((0, 0.04, 0.1 - 0.03 * t))
        box(f"Crinet{k}", (0.16 - 0.03 * t, 0.12, 0.05), c, M_TRIM if k % 2 else M_BODY,
            "h_neck2" if t > 0.5 else "h_neck1", rot=(math.radians(-40), 0, 0), bevel=0.015)

def crest(c, size):
    """Gold fleur-de-lis on the shield face (centre petal, two curled side petals, a band), bent with the shield's
    curve so it lies ON the face (a flat emblem stood off the edges where the shield bows back)."""
    n0 = len(PARTS)
    face = c + Vector((0, -0.032, 0))
    bm = lathe_bm([(0, 0), (0.04, 0.05), (0.03, 0.12), (0, 0.17)], 6)
    xform(bm, Matrix.Translation(face + Vector((0, 0, -0.02 * size))) @ Matrix.Diagonal((size, size * 0.3, size, 1)))
    new_obj(bm, "FleurCentre", M_TRIM, "shield")
    for s in (1, -1):
        pts = [Vector((s * (0.02 + 0.07 * math.sin(t * 2.4)), 0, 0.06 * math.cos(t * 2.4) - 0.01)) * size
               for t in [i / 6 for i in range(7)]]
        for i in range(6):
            rod(f"FleurSide{s}{i}", face + pts[i], face + pts[i + 1], 0.016 * size, 0.012 * size, M_TRIM, "shield", 6)
    box("FleurBand", (0.11 * size, 0.02, 0.025 * size), face + Vector((0, -0.005, -0.03 * size)), M_TRIM, "shield", bevel=0.005)
    for o in PARTS[n0:]:   # same bow as kite_shield: y += x^2 * 1.6 about the shield's centre line
        for v in o.data.vertices: v.co.y += (v.co.x - c.x) ** 2 * 1.6

KN_BLADE = 0.72   # morning-star haft length from the grip (human metres)
KN_BALL = 0.1     # radius of the spiked head

def morning_star(J, hand="R"):
    """Sheet "ナイト | 360°ビュー": a gold-banded haft with a spiked iron ball. Weapon bone Y runs up the haft from the
    grip, so anims aim it like a blade; the ball centre is KN_BLADE + KN_BALL along it."""
    w, t = J[f"wrist.{hand}"], J[f"handtip.{hand}"]
    g = w + (t - w) * 0.7
    d = Vector((0, -1, 0.15)).normalized()
    rod("MSGrip", g - d * 0.1, g + d * 0.08, 0.02, 0.02, M_TRIM, "weapon", 10)
    sphere("MSPommel", 0.03, g - d * 0.12, M_TRIM, "weapon", seg=10)
    rod("MSHaft", g + d * 0.08, g + d * KN_BLADE, 0.022, 0.026, M_BODY, "weapon", 10)
    for k, z in enumerate((0.1, 0.35, 0.6)):
        rod(f"MSBand{k}", g + d * (z - 0.015), g + d * (z + 0.015), 0.03, 0.03, M_TRIM, "weapon", 10)
    c = g + d * (KN_BLADE + KN_BALL * 0.8)
    rod("MSCollar", g + d * (KN_BLADE - 0.04), g + d * (KN_BLADE + 0.02), 0.03, 0.045, M_TRIM, "weapon", 10)
    sphere("MSBall", KN_BALL, c, M_BODY, "weapon", seg=14)
    import itertools
    dirs = [Vector(v).normalized() for v in itertools.product((-1, 0, 1), repeat=3) if any(v) and sum(abs(x) for x in v) <= 2]
    for i, u in enumerate(dirs):   # 18 short spikes
        rod(f"MSSpike{i}", c + u * KN_BALL * 0.85, c + u * KN_BALL * 1.55, 0.022, 0.002, M_TRIM, "weapon", 6)
    return g

def build_knight():
    p = {"bulk": 1.0, "leg": 1.0, "head": 1.0, "base": 0.0}
    J = rider_skeleton(p)
    J.update({k: Vector(v) for k, v in HORSE_J.items()})
    horse = horse_skin(J)
    rider = skin_body(J, p)
    horse_details(J)
    head(J, face=False)
    helmet(J, "great")
    cuirass(J, 1.0); pauldrons(J, 0.09); limb_armour(J, grip=("L", "R"))   # five-fingered fists
    # detailed sheet (2026-10-25): a long knightly sword instead of the lance, worn at the left hip for a cross draw
    g = morning_star(J)
    d = Vector((0, -1, 0.15)).normalized()
    c = kite_shield(J, 1.35, emblem=False)
    crest(c + Vector((0, 0, 0.02)), 1.35)
    regalia(J)
    hilt, dn = sheath_frame(J, "R")   # the morning star hangs head-down from a gold ring at the left hip
    lathe("MSHanger", [(0.035, -0.012), (0.05, -0.012), (0.05, 0.012), (0.035, 0.012)], M_TRIM, "hips", 12, along(hilt + dn * 0.02, hilt + dn * 0.05))
    hl = (J["handtip.R"] - J["wrist.R"]).length * 0.7
    to_sh = J["shoulder.R"] - hilt; to_sh.z = 0; to_sh.normalize()
    wr = hilt + to_sh * hl * 0.85 + Vector((0, 0.03, hl * 0.4))
    fa = J["elbow.L"] + (J["wrist.L"] - J["elbow.L"]) * 0.9
    extra = {"weapon": (g, g + d * 0.3, "hand.R"),   # bone Y along the blade
             "shield": (fa, fa + Vector((0, 0, 0.25)), "forearm.L"),
             "sheath.R": (hilt, hilt + dn * 0.2, "hips"), "hilt.R": (wr, wr + Vector((0, 0, 0.08)), "hips")}
    rider_bones = [(n, h, t, "h_hips" if n == "hips" else par) for n, h, t, par in BONES if n != "root"]
    bones = [BONES[0]] + HORSE_BONES + rider_bones
    horse_names = {b[0] for b in HORSE_BONES}
    rider_names = {b[0] for b in rider_bones}
    return dict(J=J, extra=extra, scale=0.47, bones=bones,
                bodies=[(horse, horse_names), (rider, rider_names)])

PIECES["Knight"] = build_knight
