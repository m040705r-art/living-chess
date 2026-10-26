# Living chess pieces (Battle-Chess style) for the Unity chess game.
# Run headless:  blender -b -P chess_pieces.py      (or exec(open(path).read()) inside Blender)
# Each piece = one Armature + one skinned mesh (rigid weights: every part follows exactly one bone),
# pivot at the feet, facing Blender -Y, 1 unit = 1 board square.
# The round pedestal is split into two half-disc FEET, so a piece looks normal standing still and can walk.
# Bones: Root > Hips > (Leg.L > Foot.L, Leg.R > Foot.R, Spine > Chest > (Head, UpperArm.* > ForeArm.* > Hand.* [> Weapon]))
# Materials: PieceBody (swap white/black in Unity), Trim (gold), Metal, Eye.
import os as _os, bpy as _bpy
# the repository root: $CHESS_ROOT, else the folder above the open .blend / this script (no machine paths in the repo)
CHESS = (_os.environ.get("CHESS_ROOT") or (_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))) if "__file__" in globals() else "")
         or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)) or ".").replace("\\", "/")
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

ROOT = CHESS
OUT = ROOT + "/Assets/Chess/Art/Models/Pieces"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- materials
bpy.ops.wm.read_factory_settings(use_empty=True)
def lin(c): return tuple(pow(v, 2.2) for v in c)

def mat(name, srgb, rough=0.5, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (*lin(srgb), 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    m.diffuse_color = (*lin(srgb), 1)
    return m

M_BODY = mat("PieceBody", (0.93, 0.88, 0.78), 0.35)
M_BLACK = mat("PieceBody_Black", (0.13, 0.11, 0.11), 0.3)   # preview only; Unity swaps PieceBody
M_TRIM = mat("Trim", (0.95, 0.74, 0.30), 0.3, 1.0)
M_METAL = mat("Metal", (0.78, 0.80, 0.84), 0.25, 1.0)
M_EYE = mat("Eye", (0.05, 0.05, 0.07), 0.2)

# ---------------------------------------------------------------- mesh helpers
PARTS = []   # (object, bone) for the piece being built

def new_obj(bm, name, material, bone):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(material)
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    PARTS.append(ob)
    return ob

def lathe_bm(profile, seg=20, a0=0.0, a1=2 * math.pi):
    """Spin a (r, z) profile around Z. Partial spins get flat caps."""
    bm = bmesh.new()
    full = abs((a1 - a0) - 2 * math.pi) < 1e-6
    steps = seg if full else seg
    rings = []
    for i in range(steps + (0 if full else 1)):
        a = a0 + (a1 - a0) * i / steps
        rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for r, z in profile])
    n = len(rings)
    for i in range(n if full else n - 1):
        A, B = rings[i], rings[(i + 1) % n]
        for j in range(len(profile) - 1):
            q = [A[j], B[j], B[j + 1], A[j + 1]]
            try: bm.faces.new(q)
            except ValueError: pass
    if not full:
        for ring in (rings[0], rings[-1]):
            try: bm.faces.new(ring if ring is rings[-1] else list(reversed(ring)))
            except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

def xform(bm, m):
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return bm

def lathe(name, profile, material, bone, seg=20, at=(0, 0, 0)):
    return new_obj(xform(lathe_bm(profile, seg), Matrix.Translation(at)), name, material, bone)

def sphere(name, r, at, material, bone, scale=(1, 1, 1), seg=14):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=r)
    xform(bm, Matrix.Translation(at) @ Matrix.Diagonal((*scale, 1)))
    return new_obj(bm, name, material, bone)

def box(name, size, at, material, bone, rot=(0, 0, 0), bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    xform(bm, Matrix.Diagonal((*size, 1)))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2, affect='EDGES', profile=0.5)
    e = Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X')
    xform(bm, Matrix.Translation(at) @ e)
    return new_obj(bm, name, material, bone)

def rod(name, a, b, r0, r1, material, bone, seg=12):
    """Tapered cylinder from point a to point b."""
    a, b = Vector(a), Vector(b)
    L = (b - a).length
    bm = lathe_bm([(0, 0), (r0, 0), (r1, L), (0, L)], seg)
    rot = Vector((0, 0, 1)).rotation_difference((b - a).normalized()).to_matrix().to_4x4()
    return new_obj(xform(bm, Matrix.Translation(a) @ rot), name, material, bone)

def cone(name, a, b, r, material, bone, seg=12):
    return rod(name, a, b, r, 0.0005, material, bone, seg)

# ---------------------------------------------------------------- piece layouts
# Heights: pawn 0.58 .. king 1.0 (board square = 1).
K = {
    #          base   hip   mid   neck  hipR  waist collar shX   shZ   upper fore armR  hand
    "Pawn":   (0.21, 0.13, 0.25, 0.35, 0.16, 0.085, 0.13, 0.115, 0.32, 0.085, 0.075, 0.022, 0.033),
    "Rook":   (0.26, 0.14, 0.32, 0.50, 0.20, 0.150, 0.19, 0.205, 0.43, 0.100, 0.095, 0.038, 0.060),
    "Knight": (0.24, 0.14, 0.29, 0.44, 0.18, 0.100, 0.16, 0.135, 0.40, 0.095, 0.090, 0.026, 0.036),
    "Bishop": (0.24, 0.14, 0.31, 0.50, 0.17, 0.090, 0.15, 0.125, 0.46, 0.105, 0.095, 0.024, 0.034),
    "Queen":  (0.25, 0.14, 0.35, 0.58, 0.20, 0.090, 0.17, 0.135, 0.53, 0.110, 0.105, 0.024, 0.034),
    "King":   (0.26, 0.14, 0.36, 0.60, 0.20, 0.100, 0.18, 0.145, 0.55, 0.115, 0.110, 0.027, 0.037),
}
FOOT_H = 0.055

def build_common(kind):
    base, hip, mid, neck, hipR, waist, collar, shX, shZ, up, fo, armR, handR = K[kind]
    J = {}  # joint positions for the rig
    # feet: the classic pedestal cut in half; the slim gap reads as a seam when standing
    prof = [(0, 0), (base, 0), (base, 0.025), (base * 0.92, 0.04), (base * 0.78, FOOT_H), (0, FOOT_H)]
    for side, s in (("L", 1), ("R", -1)):
        bm = lathe_bm(prof, 12, -math.pi / 2, math.pi / 2)
        xform(bm, Matrix.Translation((0.008, 0, 0)))
        if s < 0: xform(bm, Matrix.Rotation(math.pi, 4, 'Z'))
        new_obj(bm, f"Foot{side}", M_BODY, f"Foot.{side}")
        lx = s * base * 0.42
        rod(f"Leg{side}", (lx, 0, FOOT_H - 0.01), (lx, 0, hip + 0.01), 0.045, 0.05, M_BODY, f"Leg.{side}")
        J[f"Leg.{side}"] = ((lx, 0, hip), (lx, 0, FOOT_H))
        J[f"Foot.{side}"] = ((lx, 0, FOOT_H), (lx, -base * 0.6, FOOT_H))
    # body: lower skirt (Spine) and upper torso (Chest), turned like a real chess piece
    lathe("Lower", [(0, hip), (hipR, hip), (hipR, hip + 0.02), (hipR * 0.82, hip + 0.045),
                    (waist * 1.15, (hip + mid) / 2), (waist, mid + 0.005), (0, mid + 0.005)], M_BODY, "Spine")
    lathe("Upper", [(0, mid - 0.005), (waist, mid - 0.005), (waist * 1.08, mid + (neck - mid) * 0.55),
                    (collar, neck - 0.03), (collar, neck - 0.012), (collar * 0.55, neck), (0, neck)], M_BODY, "Chest")
    lathe("Belt", [(0, mid - 0.012), (waist * 1.12, mid - 0.012), (waist * 1.12, mid + 0.012), (0, mid + 0.012)],
          M_TRIM, "Spine")
    J["Root"] = ((0, 0, 0), (0, 0, hip * 0.6))
    J["Hips"] = ((0, 0, hip), (0, 0, hip + 0.04))
    J["Spine"] = ((0, 0, hip + 0.04), (0, 0, mid))
    J["Chest"] = ((0, 0, mid), (0, 0, neck))
    # arms: hang slightly out and forward
    for side, s in (("L", 1), ("R", -1)):
        sh = Vector((s * shX, 0, shZ))
        el = sh + Vector((s * 0.02, -0.01, -up))
        wr = el + Vector((0, -0.035, -fo))
        sphere(f"Shoulder{side}", armR * 1.5, sh, M_BODY, f"UpperArm.{side}", seg=10)
        rod(f"Upper{side}", sh, el, armR, armR * 0.9, M_BODY, f"UpperArm.{side}", 10)
        sphere(f"Elbow{side}", armR * 1.05, el, M_BODY, f"ForeArm.{side}", seg=8)
        rod(f"Fore{side}", el, wr, armR * 0.9, armR * 0.8, M_BODY, f"ForeArm.{side}", 10)
        hc = wr + Vector((0, 0, -handR * 0.7))
        sphere(f"Hand{side}", handR, hc, M_BODY, f"Hand.{side}", seg=10)
        J[f"UpperArm.{side}"] = (tuple(sh), tuple(el))
        J[f"ForeArm.{side}"] = (tuple(el), tuple(wr))
        J[f"Hand.{side}"] = (tuple(wr), tuple(wr + Vector((0, 0, -handR * 1.6))))
        J[f"_hand{side}"] = hc
    return J

def eyes(head_c, r, forward=0.9, spread=0.38, lift=0.12, er=0.016):
    for s in (1, -1):
        sphere(f"Eye{'L' if s > 0 else 'R'}",
               er, Vector(head_c) + Vector((s * r * spread, -r * forward, r * lift)), M_EYE, "Head", seg=8)

def weapon_bone(J, top):
    hc = J["_handR"]
    J["Weapon"] = (tuple(hc), tuple(Vector(hc) + Vector(top)))

# ---- per-kind heads and weapons
def pawn(J):
    neck = K["Pawn"][3]
    hc = (0, 0, neck + 0.1)
    lathe("Collar", [(0, neck - 0.01), (0.11, neck - 0.01), (0.11, neck + 0.015), (0, neck + 0.015)], M_BODY, "Head")
    sphere("HeadBall", 0.1, hc, M_BODY, "Head", seg=16)
    lathe("Helmet", [(0, hc[2] + 0.1), (0.07, hc[2] + 0.085), (0.103, hc[2] + 0.03), (0.108, hc[2] + 0.02),
                     (0.0, hc[2] + 0.02)], M_METAL, "Head", seg=16)
    eyes(hc, 0.1)
    J["Head"] = ((0, 0, neck), (0, 0, hc[2] + 0.1))
    h = Vector(J["_handR"])
    rod("SpearShaft", h + Vector((0, 0, -0.12)), h + Vector((0, 0, 0.36)), 0.011, 0.011, M_TRIM, "Weapon", 8)
    cone("SpearTip", h + Vector((0, 0, 0.36)), h + Vector((0, 0, 0.44)), 0.022, M_METAL, "Weapon", 8)
    weapon_bone(J, (0, 0, 0.3))
    hl = Vector(J["_handL"]) + Vector((0.025, -0.02, 0.02))
    bm = lathe_bm([(0, 0), (0.08, 0.004), (0.085, 0.016), (0, 0.022)], 16)
    xform(bm, Matrix.Translation(hl) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
    new_obj(bm, "Shield", M_METAL, "Hand.L")

def rook(J):
    neck = K["Rook"][3]
    top = neck + 0.13
    lathe("Turret", [(0, neck - 0.01), (0.17, neck - 0.01), (0.2, neck + 0.02), (0.18, top), (0, top)], M_BODY, "Head")
    for i in range(6):
        a = i * math.pi / 3
        box(f"Crenel{i}", (0.07, 0.06, 0.06), (0.15 * math.sin(a), -0.15 * math.cos(a), top + 0.025),
            M_BODY, "Head", rot=(0, 0, a), bevel=0.006)
    for s in (1, -1):   # eye slits on the turret front
        box(f"Slit{'L' if s > 0 else 'R'}", (0.045, 0.02, 0.018), (s * 0.055, -0.19, neck + 0.075), M_EYE, "Head",
            rot=(0, -s * 0.25, 0))
    lathe("TurretBand", [(0, neck + 0.02), (0.205, neck + 0.02), (0.205, neck + 0.04), (0, neck + 0.04)], M_TRIM, "Head")
    J["Head"] = ((0, 0, neck), (0, 0, top + 0.06))
    # no weapon: big stone fists (already sized by hand radius); bone kept for consistency
    weapon_bone(J, (0, -0.1, 0))

def knight(J):
    neck = K["Knight"][3]
    box("HorseNeck", (0.1, 0.12, 0.2), (0, 0.0, neck + 0.08), M_BODY, "Head", rot=(math.radians(18), 0, 0), bevel=0.02)
    box("HorseHead", (0.1, 0.2, 0.1), (0, -0.09, neck + 0.18), M_BODY, "Head", rot=(math.radians(-22), 0, 0), bevel=0.025)
    box("Muzzle", (0.085, 0.07, 0.075), (0, -0.18, neck + 0.14), M_BODY, "Head", rot=(math.radians(-22), 0, 0), bevel=0.02)
    box("Mane", (0.03, 0.05, 0.24), (0, 0.06, neck + 0.12), M_TRIM, "Head", rot=(math.radians(18), 0, 0), bevel=0.01)
    for s in (1, -1):
        cone(f"Ear{'L' if s > 0 else 'R'}", (s * 0.03, -0.02, neck + 0.22), (s * 0.04, 0.0, neck + 0.29), 0.018,
             M_BODY, "Head", 8)
        sphere(f"Eye{'L' if s > 0 else 'R'}", 0.014, (s * 0.05, -0.1, neck + 0.2), M_EYE, "Head", seg=8)
        sphere(f"Nostril{'L' if s > 0 else 'R'}", 0.008, (s * 0.022, -0.22, neck + 0.135), M_EYE, "Head", seg=6)
    J["Head"] = ((0, 0, neck), (0, -0.05, neck + 0.28))
    sword(J, 0.3)

def sword(J, L):
    h = Vector(J["_handR"])
    rod("Grip", h + Vector((0, 0, -0.045)), h + Vector((0, 0, 0.03)), 0.011, 0.011, M_TRIM, "Weapon", 8)
    sphere("Pommel", 0.018, h + Vector((0, 0, -0.05)), M_TRIM, "Weapon", seg=8)
    box("Guard", (0.1, 0.022, 0.018), h + Vector((0, 0, 0.035)), M_TRIM, "Weapon", bevel=0.005)
    box("Blade", (0.034, 0.008, L), h + Vector((0, 0, 0.045 + L / 2)), M_METAL, "Weapon")
    cone("BladeTip", h + Vector((0, 0, 0.045 + L)), h + Vector((0, 0, 0.045 + L + 0.035)), 0.02, M_METAL, "Weapon", 4)
    weapon_bone(J, (0, 0, L))

def bishop(J):
    neck = K["Bishop"][3]
    hc = (0, 0, neck + 0.08)
    sphere("Face", 0.085, hc, M_BODY, "Head", seg=16)
    m0 = hc[2] + 0.04
    lathe("Mitre", [(0, m0), (0.088, m0), (0.095, m0 + 0.05), (0.08, m0 + 0.12), (0.04, m0 + 0.18),
                    (0.0, m0 + 0.21)], M_BODY, "Head", seg=18)
    sphere("MitreBall", 0.025, (0, 0, m0 + 0.225), M_BODY, "Head", seg=10)
    lathe("MitreBand", [(0, m0 - 0.005), (0.092, m0 - 0.005), (0.092, m0 + 0.015), (0, m0 + 0.015)], M_TRIM, "Head")
    box("MitreSlit", (0.012, 0.03, 0.12), (0.02, -0.075, m0 + 0.1), M_EYE, "Head", rot=(0, math.radians(25), 0))
    eyes(hc, 0.085)
    J["Head"] = ((0, 0, neck), (0, 0, m0 + 0.25))
    h = Vector(J["_handR"])
    rod("Staff", h + Vector((0, 0, -0.2)), h + Vector((0, 0, 0.4)), 0.012, 0.012, M_TRIM, "Weapon", 8)
    bm = bmesh.new()  # crozier curl: a half torus
    c = h + Vector((0, -0.045, 0.4))
    ring = []
    for i in range(13):
        a = math.pi * i / 12
        ring.append(c + Vector((0, 0.045 * math.cos(a), 0.045 * math.sin(a))))
    for i in range(12):
        rod(f"Curl{i}", ring[i], ring[i + 1], 0.012, 0.012, M_TRIM, "Weapon", 8)
    bm.free()
    weapon_bone(J, (0, 0, 0.4))

def queen(J):
    neck = K["Queen"][3]
    hc = (0, 0, neck + 0.09)
    lathe("Ruff", [(0, neck - 0.01), (0.13, neck - 0.005), (0.11, neck + 0.02), (0, neck + 0.02)], M_TRIM, "Head")
    sphere("HeadBall", 0.095, hc, M_BODY, "Head", seg=16)
    c0 = hc[2] + 0.055
    lathe("Crown", [(0, c0), (0.075, c0), (0.11, c0 + 0.07), (0.1, c0 + 0.075), (0.065, c0 + 0.01), (0, c0 + 0.01)],
          M_TRIM, "Head", seg=16)
    for i in range(8):
        a = i * math.pi / 4
        sphere(f"CrownPt{i}", 0.017, (0.105 * math.cos(a), 0.105 * math.sin(a), c0 + 0.085), M_TRIM, "Head", seg=8)
    sphere("CrownJewel", 0.03, (0, 0, c0 + 0.06), M_BODY, "Head", seg=10)
    eyes(hc, 0.095)
    J["Head"] = ((0, 0, neck), (0, 0, c0 + 0.1))
    h = Vector(J["_handR"])
    rod("Scepter", h + Vector((0, 0, -0.08)), h + Vector((0, 0, 0.26)), 0.011, 0.014, M_TRIM, "Weapon", 8)
    sphere("ScepterOrb", 0.035, h + Vector((0, 0, 0.29)), M_METAL, "Weapon", seg=12)
    for i in range(4):
        a = i * math.pi / 2
        cone(f"Star{i}", h + Vector((0, 0, 0.29)), h + Vector((0.07 * math.cos(a), 0, 0.29 + 0.07 * math.sin(a))),
             0.012, M_TRIM, "Weapon", 4)
    weapon_bone(J, (0, 0, 0.3))

def king(J):
    neck = K["King"][3]
    hc = (0, 0, neck + 0.1)
    lathe("Collar", [(0, neck - 0.01), (0.13, neck - 0.01), (0.13, neck + 0.02), (0, neck + 0.02)], M_TRIM, "Head")
    sphere("HeadBall", 0.1, hc, M_BODY, "Head", seg=16)
    sphere("Beard", 0.07, (0, -0.06, hc[2] - 0.06), M_BODY, "Head", scale=(1.0, 0.7, 1.1), seg=12)
    c0 = hc[2] + 0.055
    lathe("Crown", [(0, c0), (0.095, c0), (0.105, c0 + 0.08), (0.09, c0 + 0.08), (0.08, c0 + 0.012), (0, c0 + 0.012)],
          M_TRIM, "Head", seg=16)
    box("CrossV", (0.03, 0.03, 0.13), (0, 0, c0 + 0.13), M_TRIM, "Head", bevel=0.005)
    box("CrossH", (0.09, 0.03, 0.03), (0, 0, c0 + 0.15), M_TRIM, "Head", bevel=0.005)
    eyes(hc, 0.1)
    J["Head"] = ((0, 0, neck), (0, 0, c0 + 0.2))
    sword(J, 0.36)

BUILD = {"Pawn": pawn, "Rook": rook, "Knight": knight, "Bishop": bishop, "Queen": queen, "King": king}
PARENT = {"Root": None, "Hips": "Root", "Spine": "Hips", "Chest": "Spine", "Head": "Chest",
          "Leg.L": "Hips", "Foot.L": "Leg.L", "Leg.R": "Hips", "Foot.R": "Leg.R",
          "UpperArm.L": "Chest", "ForeArm.L": "UpperArm.L", "Hand.L": "ForeArm.L",
          "UpperArm.R": "Chest", "ForeArm.R": "UpperArm.R", "Hand.R": "ForeArm.R", "Weapon": "Hand.R"}

# ---------------------------------------------------------------- assemble
def make_piece(kind):
    PARTS.clear()
    J = build_common(kind)
    BUILD[kind](J)
    # one mesh
    with bpy.context.temp_override(active_object=PARTS[0], selected_editable_objects=PARTS, object=PARTS[0]):
        bpy.ops.object.join()
    mesh_ob = PARTS[0]
    mesh_ob.name = kind + "_Mesh"; mesh_ob.data.name = kind + "_Mesh"
    me = mesh_ob.data
    for p in me.polygons: p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(35))
    # armature
    arm = bpy.data.armatures.new(kind + "_Rig")
    rig = bpy.data.objects.new(kind, arm)
    bpy.context.scene.collection.objects.link(rig)
    arm.display_type = 'STICK'
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for name, parent in PARENT.items():
        h, t = J[name]
        eb = arm.edit_bones.new(name)
        eb.head, eb.tail = Vector(h), Vector(t)
        if (eb.tail - eb.head).length < 1e-4: eb.tail = eb.head + Vector((0, 0, 0.05))
        eb.roll = 0
        if parent:
            eb.parent = arm.edit_bones[parent]
            eb.use_connect = False
        eb.use_deform = name != "Root"
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh_ob.parent = rig
    mod = mesh_ob.modifiers.new("Armature", 'ARMATURE')
    mod.object = rig
    return rig, mesh_ob

def export(rig, mesh_ob):
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); mesh_ob.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, rig.name + ".fbx"), use_selection=True,
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', bake_space_transform=False,
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE',
                             object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
                             primary_bone_axis='Y', secondary_bone_axis='X', bake_anim=False)

def main():
    order = ["Pawn", "Rook", "Knight", "Bishop", "Queen", "King"]
    rigs = []
    for i, kind in enumerate(order):
        rig, mesh_ob = make_piece(kind)
        export(rig, mesh_ob)
        rig.location.x = (i - 2.5) * 0.75   # line up for viewing; files were exported at the origin
        rigs.append((rig, mesh_ob))
        print("built", kind, len(mesh_ob.data.polygons), "faces")
    bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/BlenderSource/chess_pieces.blend")
    return rigs

if __name__ == "__main__" or True:
    _rigs = main()
