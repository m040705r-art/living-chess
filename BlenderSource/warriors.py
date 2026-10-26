# Statue-like warrior chess pieces (marble / obsidian), modelled after the user's reference sheet.
# Run inside Blender (MCP: exec(open(path).read())) or headless: blender -b -P warriors.py
# Body = Skin-modifier humanoid (auto weights); armour/weapons = rigid parts weighted to one bone each.
# Modelled at human scale (1.8 m) facing -Y, then scaled by SCALE so 1 unit = 1 board square.
import os as _os, bpy as _bpy
# the repository root: $CHESS_ROOT, else the folder above the open .blend / this script (no machine paths in the repo)
CHESS = (_os.environ.get("CHESS_ROOT") or (_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))) if "__file__" in globals() else "")
         or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)) or ".").replace("\\", "/")
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

ROOT = CHESS
OUT = ROOT + "/Assets/Chess/Art/Models/Pieces"
os.makedirs(OUT, exist_ok=True)

def clear_scene():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.cameras):
        for d in list(coll): coll.remove(d)

# ---------------------------------------------------------------- materials
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

def materials():
    global M_BODY, M_BLACK, M_TRIM, M_DARK, M_GLOW
    M_BODY = mat("PieceBody", (0.74, 0.74, 0.72), 0.55)          # pale stone; Unity swaps for dark stone
    M_BLACK = mat("PieceBody_Black", (0.16, 0.16, 0.17), 0.45)   # preview only
    M_TRIM = mat("Trim", (0.83, 0.66, 0.36), 0.35, 1.0)   # gilded trim (design board: gold accents on the stone)
    M_DARK = mat("Shadow", (0.04, 0.04, 0.05), 0.6)              # visor slits, eye sockets
    M_GLOW = mat("Glow", (0.6, 0.8, 1.0), 0.2)                  # magic focus (bishop's orb); emissive
    b = next(n for n in M_GLOW.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Emission Color'].default_value = (0.5, 0.75, 1.0, 1); b.inputs['Emission Strength'].default_value = 4.0

# ---------------------------------------------------------------- mesh helpers
PARTS = []
AUTO = []   # cloth-like parts: joined into the body before auto weights so they deform with the legs

def new_obj(bm, name, material, bone):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(material)
    if bone == "AUTO":
        AUTO.append(ob); return ob
    if bone:
        ob.vertex_groups.new(name=bone).add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    PARTS.append(ob)
    return ob

def xform(bm, m):
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return bm

def rotm(rot):
    return (Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X'))

def lathe_bm(profile, seg=20, a0=0.0, a1=2 * math.pi):
    bm = bmesh.new()
    full = abs((a1 - a0) - 2 * math.pi) < 1e-6
    rings = []
    for i in range(seg + (0 if full else 1)):
        a = a0 + (a1 - a0) * i / seg
        rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for r, z in profile])
    n = len(rings)
    for i in range(n if full else n - 1):
        A, B = rings[i], rings[(i + 1) % n]
        for j in range(len(profile) - 1):
            try: bm.faces.new([A[j], B[j], B[j + 1], A[j + 1]])
            except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

def lathe(name, profile, material, bone, seg=20, m=Matrix()):
    return new_obj(xform(lathe_bm(profile, seg), m), name, material, bone)

def shell(name, profile, material, bone, seg=20, m=Matrix(), a0=0.0, a1=2 * math.pi, thick=0.012):
    """Lathed surface with thickness (open armour plates)."""
    bm = lathe_bm(profile, seg, a0, a1)
    if thick:
        res = bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thick)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(xform(bm, m), name, material, bone)

def sphere(name, r, at, material, bone, scale=(1, 1, 1), seg=16, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=r)
    xform(bm, Matrix.Translation(at) @ rotm(rot) @ Matrix.Diagonal((*scale, 1)))
    return new_obj(bm, name, material, bone)

def box(name, size, at, material, bone, rot=(0, 0, 0), bevel=0.0, taper=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if taper:   # scale the top (+z) face: (sx, sy)
        for v in bm.verts:
            if v.co.z > 0: v.co.x *= taper[0]; v.co.y *= taper[1]
    xform(bm, Matrix.Diagonal((*size, 1)))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2, affect='EDGES', profile=0.5)
    xform(bm, Matrix.Translation(at) @ rotm(rot))
    return new_obj(bm, name, material, bone)

def rod(name, a, b, r0, r1, material, bone, seg=12):
    a, b = Vector(a), Vector(b)
    bm = lathe_bm([(0, 0), (r0, 0), (r1, (b - a).length), (0, (b - a).length)], seg)
    rot = Vector((0, 0, 1)).rotation_difference((b - a).normalized()).to_matrix().to_4x4()
    return new_obj(xform(bm, Matrix.Translation(a) @ rot), name, material, bone)

def along(a, b):
    """Matrix placing local +Z along a->b, origin at a."""
    a, b = Vector(a), Vector(b)
    return Matrix.Translation(a) @ Vector((0, 0, 1)).rotation_difference((b - a).normalized()).to_matrix().to_4x4()

# ---------------------------------------------------------------- humanoid skeleton
PROP = {}

def skeleton(p):
    """Joint positions (human scale). p: bulk (width), leg (leg length factor), head (head size)."""
    PROP.clear(); PROP.update(p)
    b, lf = p.get("bulk", 1.0), p.get("leg", 1.0)
    dz = 0.95 * (lf - 1)          # upper body drops with shorter legs
    bh = p.get("base", 0.0)       # statue pedestal height
    up = lambda x, y, z: (x, y, z + dz + bh)
    J = {"root": (0, 0, 0), "hips": up(0, 0, 0.95), "spine": up(0, 0, 1.08), "chest": up(0, 0, 1.27),
         "neck": up(0, 0, 1.48), "head": up(0, 0, 1.56), "head_end": up(0, 0, 1.56 + 0.24 * p.get("head", 1.0))}
    for s, L in ((1, "L"), (-1, "R")):
        J[f"clav.{L}"] = up(s * 0.03, 0, 1.44)
        J[f"shoulder.{L}"] = up(s * 0.21 * b, 0, 1.42)
        J[f"elbow.{L}"] = up(s * 0.36 * b, 0.03, 1.2)
        J[f"wrist.{L}"] = up(s * 0.48 * b, -0.02, 1.0)
        J[f"handtip.{L}"] = up(s * 0.53 * b, -0.04, 0.93)
        J[f"hip.{L}"] = up(s * 0.105 * b, 0, 0.93)
        J[f"knee.{L}"] = (s * 0.11 * b, -0.02, 0.09 + 0.42 * lf + bh)
        J[f"ankle.{L}"] = (s * 0.11 * b, 0.02, 0.09 + bh)
        J[f"toe.{L}"] = (s * 0.11 * b, -0.13, 0.03 + bh)
    return {k: Vector(v) for k, v in J.items()}

BONES = [  # name, head joint, tail joint, parent
    ("root", "root", None, None),
    ("hips", "hips", "spine", "root"),
    ("spine", "spine", "chest", "hips"),
    ("chest", "chest", "neck", "spine"),
    ("neck", "neck", "head", "chest"),
    ("head", "head", "head_end", "neck"),
]
for L in ("L", "R"):
    BONES += [
        (f"shoulder.{L}", f"clav.{L}", f"shoulder.{L}", "chest"),
        (f"upper_arm.{L}", f"shoulder.{L}", f"elbow.{L}", f"shoulder.{L}"),
        (f"forearm.{L}", f"elbow.{L}", f"wrist.{L}", f"upper_arm.{L}"),
        (f"hand.{L}", f"wrist.{L}", f"handtip.{L}", f"forearm.{L}"),
        (f"thigh.{L}", f"hip.{L}", f"knee.{L}", "hips"),
        (f"shin.{L}", f"knee.{L}", f"ankle.{L}", f"thigh.{L}"),
        (f"foot.{L}", f"ankle.{L}", f"toe.{L}", f"shin.{L}"),
    ]

def skin_body(J, p):
    """Organic base body from a Skin modifier graph (covered by armour/robes, so kept simple)."""
    b = p.get("bulk", 1.0)
    nodes = [  # (joint or point, radius x, radius y)
        ("hips", 0.17 * b, 0.125), ("spine", 0.16 * b, 0.115), ("chest", 0.2 * b, 0.135),
        ("neck", 0.065, 0.065),
    ]
    edges = [(0, 1), (1, 2), (2, 3)]
    def add(pos, rx, ry, link):
        nodes.append((pos, rx, ry)); edges.append((link, len(nodes) - 1)); return len(nodes) - 1
    for L in ("L", "R"):
        i = add(f"shoulder.{L}", 0.078 * b, 0.078 * b, 2)
        i = add(f"elbow.{L}", 0.058 * b, 0.058 * b, i)
        i = add(f"wrist.{L}", 0.046 * b, 0.046 * b, i)
        add(f"handtip.{L}", 0.04, 0.04, i)
        i = add(f"hip.{L}", 0.105 * b, 0.105 * b, 0)
        i = add(f"knee.{L}", 0.072 * b, 0.072 * b, i)
        i = add(f"ankle.{L}", 0.052 * b, 0.052 * b, i)
        add(f"toe.{L}", 0.045, 0.038, i)
    me = bpy.data.meshes.new("Body")
    me.from_pydata([tuple(J[n] if isinstance(n, str) else n) for n, _, _ in nodes], edges, [])
    ob = bpy.data.objects.new("Body", me)
    bpy.context.scene.collection.objects.link(ob)
    sk = ob.modifiers.new("Skin", 'SKIN')
    for i, (_, rx, ry) in enumerate(nodes):
        me.skin_vertices[0].data[i].radius = (rx, ry)
    me.skin_vertices[0].data[0].use_root = True
    ob.modifiers.new("Sub", 'SUBSURF').levels = 2
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear(); ob.data = me2; bpy.data.meshes.remove(me)
    me2.materials.append(M_BODY)
    return ob

# ---------------------------------------------------------------- armour kit (human scale, rigid parts)
def headm(J):
    hs = PROP.get("head", 1.0)
    return Matrix.Translation(J["head"]) @ Matrix.Diagonal((hs, hs, hs, 1)) @ Matrix.Translation(-J["head"])

def helmet(J, kind="sallet"):
    n0 = len(PARTS); _helmet(J, kind)
    for o in PARTS[n0:]: o.data.transform(headm(J))

def _helmet(J, kind):
    h = J["head"] + Vector((0, 0, 0.1))
    if kind == "sallet":   # rounded war helmet with a brim and visor slit
        shell("Helmet", [(0.0, 0.135), (0.06, 0.13), (0.105, 0.09), (0.125, 0.02), (0.13, -0.05), (0.14, -0.10),
                         (0.165, -0.12)], M_BODY, "head", 24, Matrix.Translation(h), thick=0.012)
        rod("HelmetCrest", h + Vector((0, 0.11, 0.08)), h + Vector((0, -0.11, 0.08)), 0.018, 0.018, M_BODY, "head", 8)
        box("Visor", (0.15, 0.03, 0.022), h + Vector((0, -0.118, -0.0)), M_DARK, "head")
    elif kind == "kettle":   # open-faced war hat with a broad sloping brim and a centre ridge
        shell("Helmet", [(0.0, 0.13), (0.06, 0.125), (0.1, 0.095), (0.118, 0.04), (0.122, 0.0), (0.13, -0.02),
                         (0.175, -0.05), (0.19, -0.065)], M_BODY, "head", 32, Matrix.Translation(h), thick=0.014)
        rod("HelmetRidge", h + Vector((0, 0.1, 0.07)), h + Vector((0, -0.1, 0.07)), 0.014, 0.014, M_BODY, "head", 10)
        shell("BrimLip", [(0.188, -0.068), (0.192, -0.058)], M_TRIM, "head", 32, Matrix.Translation(h), thick=0.01)
    elif kind == "bascinet":   # rounded, slightly pointed skull with cheek guards and a nasal
        shell("Helmet", [(0.117, 0.06), (0.125, 0.0), (0.122, -0.06), (0.115, -0.11)], M_BODY, "head", 32,
              Matrix.Translation(h), a0=math.radians(-35), a1=math.radians(215), thick=0.014)
        shell("HelmetFace", [(0.0, 0.15), (0.045, 0.14), (0.09, 0.11), (0.117, 0.06), (0.121, 0.03)], M_BODY, "head", 32,
              Matrix.Translation(h))   # closed brow; the open face below it shows the carved face
        shell("HelmetBand", [(0.127, -0.01), (0.129, 0.02)], M_TRIM, "head", 32, Matrix.Translation(h), thick=0.012)
        box("Nasal", (0.024, 0.02, 0.1), h + Vector((0, -0.124, -0.03)), M_BODY, "head", bevel=0.006)
    elif kind == "great":
        lathe("Helmet", [(0, 0.12), (0.07, 0.115), (0.115, 0.07), (0.122, -0.02), (0.118, -0.12), (0, -0.12)],
              M_BODY, "head", 20, Matrix.Translation(h))
        box("Visor", (0.15, 0.03, 0.018), h + Vector((0, -0.115, 0.0)), M_DARK, "head")
        box("Breaths", (0.012, 0.03, 0.06), h + Vector((0.04, -0.112, -0.06)), M_DARK, "head")

def head(J, beard=False, face=True):
    n0 = len(PARTS); _head(J, beard, face)
    for o in PARTS[n0:]: o.data.transform(headm(J))
    hs = PROP.get("head", 1.0)   # mail aventail drapes from the head over the shoulders
    n = J["neck"]
    shell("Aventail", [(0.1 * hs, 0.17), (0.11 * hs, 0.08), (0.13, 0.0), (0.2, -0.07), (0.23, -0.1)], M_BODY, "neck", 32,
          Matrix.Translation(n) @ Matrix.Diagonal((1, 0.85, 1, 1)), thick=0.012)

def _head(J, beard, face):
    h = J["head"] + Vector((0, 0, 0.1))
    sphere("Head", 0.1, h, M_BODY, "head", scale=(0.9, 1.0, 1.15), seg=18)
    if face:
        box("Brow", (0.09, 0.03, 0.022), h + Vector((0, -0.085, 0.045)), M_BODY, "head", bevel=0.008)
        box("Nose", (0.022, 0.04, 0.05), h + Vector((0, -0.098, -0.005)), M_BODY, "head", rot=(-0.3, 0, 0), bevel=0.006)
    if beard:
        sphere("Beard", 0.075, h + Vector((0, -0.055, -0.085)), M_BODY, "head", scale=(1.0, 0.75, 1.2), seg=14)

def cuirass(J, b=1.0):
    c = (J["spine"] + J["chest"]) / 2
    shell("Cuirass", [(0.18 * b, -0.17), (0.195 * b, -0.05), (0.215 * b, 0.08), (0.2 * b, 0.18), (0.1, 0.24)],
          M_BODY, "chest", 32, Matrix.Translation(c) @ Matrix.Diagonal((1, 0.75, 1, 1)), thick=0.016)
    rod("Keel", c + Vector((0, -0.165 * b, -0.14)), c + Vector((0, -0.16 * b, 0.16)), 0.012, 0.012, M_BODY, "chest", 8)

def skirt_weights(ob, top_z, bottom_z, half_w):
    """Cloth hanging from the waist: hips at the top, blending into each thigh toward the hem."""
    vg = {n: ob.vertex_groups.new(name=n) for n in ("hips", "thigh.L", "thigh.R")}
    for v in ob.data.vertices:
        t = min(1.0, max(0.0, (top_z - v.co.z) / (top_z - bottom_z))) ** 1.3
        sx = min(1.0, max(-1.0, v.co.x / half_w))
        l = 0.5 + 0.5 * sx; l = l * l * (3 - 2 * l)
        vg["hips"].add([v.index], 1.0 - t * 0.85, 'REPLACE')
        vg["thigh.L"].add([v.index], t * 0.85 * l, 'REPLACE')
        vg["thigh.R"].add([v.index], t * 0.85 * (1 - l), 'REPLACE')

def surcoat(J, length=0.55, b=1.0):
    """Knee-length tabard over the armour, weighted to hips/thighs so it swings with the legs."""
    top = J["spine"] - Vector((0, 0, 0.03))
    m = Matrix.Translation(top) @ Matrix.Diagonal((1, 0.8, 1, 1))
    prof = [(0.19 * b, 0.0), (0.205 * b, -0.12), (0.235 * b, -0.3), (0.27 * b, -length)]
    for o in (shell("Surcoat", prof, M_BODY, None, 32, m, thick=0.014),
              shell("Hem", [(0.272 * b, -length + 0.03), (0.275 * b, -length - 0.005)], M_TRIM, None, 32, m, thick=0.012)):
        skirt_weights(o, top.z, top.z - length, 0.16 * b)
    lathe("Belt", [(0, -0.03), (0.2 * b, -0.03), (0.205 * b, 0.03), (0, 0.03)], M_TRIM, "spine", 32, m)
    box("Buckle", (0.06, 0.02, 0.06), top + Vector((0, -0.165 * b, 0)), M_TRIM, "spine", bevel=0.008)

def pauldrons(J, r=0.11):
    for L, s in (("L", 1), ("R", -1)):
        m = Matrix.Translation(J[f"shoulder.{L}"] + Vector((s * 0.02, 0, 0.015))) @ Matrix.Rotation(-s * 0.5, 4, 'Y')
        shell(f"Pauldron{L}", [(0.0, r), (r * 0.7, r * 0.78), (r, r * 0.25), (r * 1.1, -r * 0.3)], M_BODY,
              f"upper_arm.{L}", 24, m, thick=0.014)
        shell(f"Lame{L}", [(r * 1.0, -r * 0.2), (r * 1.12, -r * 0.62)], M_BODY, f"upper_arm.{L}", 24,
              m @ Matrix.Translation((0, 0, -0.02)), thick=0.012)

def tassets(J, length=0.22, b=1.0, flare=1.25):
    top = J["hips"] + Vector((0, 0, 0.06))
    shell("Tassets", [(0.165 * b, 0.0), (0.2 * b * flare, -length)], M_BODY, "hips", 24,
          Matrix.Translation(top) @ Matrix.Diagonal((1, 0.8, 1, 1)), thick=0.012)

def oriented_box(name, c, axes, size, material, bone, bevel=0.006):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    if bevel: bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, affect='EDGES')
    M = Matrix((axes[0] * size[0], axes[1] * size[1], axes[2] * size[2])).transposed().to_4x4()
    M.translation = c
    return new_obj(xform(bm, M), name, material, bone)

def fist(J, side, along=0.7, grip_r=0.016, s=1.0):
    """A closed five-fingered fist around a weapon grip (user: "五本指で武器を握ってる様子にして").
    The grip runs along the hand bone's -X: anims.natural_wrist turns the hand so the blade lies there.
    Four fingers wrap the grip from the knuckles round to the palm, the thumb locks over them."""
    w, ht = J[f"wrist.{side}"], J[f"handtip.{side}"]
    Y = (ht - w).normalized()
    Z = Vector((0, -1, 0)); Z = (Z - Y * Y.dot(Z)).normalized()   # make_rig: align_roll(-Y)
    A = -(Y.cross(Z))                                            # grip axis = blade direction (index finger end)
    N = A.cross(Y)
    c = w + (ht - w) * along                                     # grip centre
    bone = f"hand.{side}"
    r = grip_r + 0.011 * s
    # back of the hand + palm: a block from the wrist to the knuckles, lying against the grip
    oriented_box(f"Palm{side}", c - Y * 0.02 * s - N * (grip_r + 0.012 * s), (A, Y, N), (0.08 * s, 0.075 * s, 0.03 * s), M_BODY, bone)
    for i, (a, fr) in enumerate(((0.027, 0.0115), (0.009, 0.012), (-0.009, 0.0115), (-0.026, 0.0105))):   # index .. little
        pts = []
        for t in (-75, -10, 55, 115, 170):   # palm side (-N) -> far side (+Y) -> front (+N) -> tips tucked toward the wrist
            tt = math.radians(t)
            pts.append(c + A * a * s + (Y * math.cos(tt) + N * math.sin(tt)) * r)
        for k in range(len(pts) - 1):
            rod(f"Finger{side}{i}_{k}", pts[k], pts[k + 1], fr * s, fr * s * 0.95, M_BODY, bone, 8)
        for k in range(1, 4):
            sphere(f"Knuckle{side}{i}_{k}", fr * s * 1.05, pts[k], M_BODY, bone, seg=8)
    # thumb: from the heel of the palm, over the index and middle fingers
    t0 = c - Y * 0.035 * s - N * (grip_r + 0.01 * s) + A * 0.03 * s
    t1 = c - Y * 0.012 * s + N * (r + 0.008 * s) + A * 0.03 * s
    t2 = c + Y * 0.004 * s + N * (r + 0.01 * s) + A * 0.012 * s
    rod(f"Thumb{side}0", t0, t1, 0.014 * s, 0.012 * s, M_BODY, bone, 8)
    rod(f"Thumb{side}1", t1, t2, 0.012 * s, 0.01 * s, M_BODY, bone, 8)
    sphere(f"ThumbJoint{side}", 0.0125 * s, t1, M_BODY, bone, seg=8)

def limb_armour(J, grip=(), grip_r=None, along=None):
    b = PROP.get("bulk", 1.0)
    for L in ("L", "R"):
        hp, k, a = J[f"hip.{L}"], J[f"knee.{L}"], J[f"ankle.{L}"]
        rod(f"Cuisse{L}", k + Vector((0, 0, 0.05)), hp - Vector((0, 0, 0.06)), 0.085 * b, 0.1 * b, M_BODY, f"thigh.{L}", 18)
        rod(f"Greave{L}", a + Vector((0, 0, 0.05)), k - Vector((0, 0, 0.03)), 0.068 * b, 0.084 * b, M_BODY, f"shin.{L}", 18)
        sphere(f"Knee{L}", 0.08 * b, k + Vector((0, -0.02, 0)), M_BODY, f"shin.{L}", scale=(1, 0.85, 1), seg=16)
        t, f = J[f"ankle.{L}"], J[f"toe.{L}"]
        box(f"Boot{L}", (0.13 * b, 0.27, 0.1), (t.x, (t.y + f.y) / 2 - 0.02, t.z - 0.04), M_BODY, f"foot.{L}",
            bevel=0.04, taper=(0.85, 0.75))
        rod(f"BootCuff{L}", a - Vector((0, 0, 0.03)), a + Vector((0, 0, 0.07)), 0.075 * b, 0.078 * b, M_BODY, f"shin.{L}", 18)
        e, w, ht = J[f"elbow.{L}"], J[f"wrist.{L}"], J[f"handtip.{L}"]
        sphere(f"Couter{L}", 0.066 * b, e, M_BODY, f"forearm.{L}", seg=14)
        rod(f"Vambrace{L}", e + (w - e) * 0.12, w, 0.06 * b, 0.066 * b, M_BODY, f"forearm.{L}", 16)
        rod(f"Cuff{L}", w - (w - e) * 0.12, w - (w - e) * 0.01, 0.062 * b, 0.068 * b, M_BODY, f"forearm.{L}", 16)   # stops at the wrist: the fist shows
        if L in grip: fist(J, L, (along or {}).get(L, 0.7), (grip_r or {}).get(L, 0.016), b)
        else: sphere(f"Fist{L}", 0.055 * b, w + (ht - w) * 0.75, M_BODY, f"hand.{L}", scale=(0.9, 1.0, 1.1), seg=14)

def sword(J, L=0.75, hand="R", bone="weapon", guard=1.0, width=0.032):
    """Blade points along hand->tip direction (rest pose); grip centred in the fist."""
    w, t = J[f"wrist.{hand}"], J[f"handtip.{hand}"]
    g = w + (t - w) * 0.7
    d = Vector((0, -1, 0.15)).normalized()   # held forward, slightly up
    rod("Grip", g - d * 0.07, g + d * 0.07, 0.016, 0.016, M_TRIM, bone, 8)
    sphere("Pommel", 0.025, g - d * 0.085, M_TRIM, bone, seg=10)
    m = along(g + d * 0.07, g + d * 0.1)
    new_obj(xform(xform(lathe_bm([(0, 0), (0.1, 0), (0.1, 0.025), (0, 0.025)], 4), Matrix.Diagonal((0.18, 1.2 * guard, 1, 1))), m),
            "Guard", M_TRIM, bone)
    bm = bmesh.new()   # flat blade with a diamond section, tapering to a point
    pts = []
    for i, z in enumerate((0.0, L * 0.85, L)):
        wdt = width if i < 2 else 0.0
        pts.append([bm.verts.new((x, y, z)) for x, y in ((wdt, 0), (0, 0.008 if i < 2 else 0), (-wdt, 0), (0, -0.008 if i < 2 else 0))])
    for i in range(2):
        for j in range(4):
            try: bm.faces.new([pts[i][j], pts[i][(j + 1) % 4], pts[i + 1][(j + 1) % 4], pts[i + 1][j]])
            except ValueError: pass
    bm.faces.new(list(reversed(pts[0])))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    new_obj(xform(bm, along(g + d * 0.1, g + d * 2) @ Matrix.Rotation(math.pi / 2, 4, 'Z')), "Blade", M_BODY, bone)
    return g

def spear(J, L=1.7, hand="R"):
    """Heavy boar-spear: thick shaft, binding rings, lugged socket, broad leaf head.
    Shaft along +Z through the fist (rest pose); the weapon bone runs up the shaft so anims can aim it."""
    w, t = J[f"wrist.{hand}"], J[f"handtip.{hand}"]
    g = w + (t - w) * 0.75
    lo, hi = g - Vector((0, 0, L * 0.55)), g + Vector((0, 0, L * 0.45))
    Z = Vector((0, 0, 1))
    rod("Shaft", lo, hi, 0.04, 0.035, M_BODY, "weapon", 14)
    rod("Butt", lo - Z * 0.07, lo + Z * 0.03, 0.03, 0.046, M_TRIM, "weapon", 14)
    sphere("ButtKnob", 0.034, lo - Z * 0.075, M_TRIM, "weapon", seg=12)
    for k, z in enumerate((0.12, 0.62, 0.86)):           # binding rings along the haft
        rod(f"Ring{k}", lo + Z * (L * z - 0.02), lo + Z * (L * z + 0.02), 0.045, 0.045, M_TRIM, "weapon", 14)
    rod("Socket", hi - Z * 0.12, hi + Z * 0.04, 0.04, 0.05, M_TRIM, "weapon", 14)
    box("Lugs", (0.2, 0.035, 0.04), hi - Z * 0.03, M_TRIM, "weapon", bevel=0.01)   # cross-lugs under the head
    bm = lathe_bm([(0, 0), (0.085, 0.07), (0.088, 0.14), (0.05, 0.25), (0, 0.34)], 4)   # broad leaf head
    xform(bm, Matrix.Translation(hi + Z * 0.04) @ Matrix.Rotation(math.pi / 4, 4, 'Z') @ Matrix.Diagonal((1, 0.42, 1, 1)))
    new_obj(bm, "SpearHead", M_BODY, "weapon")
    return g

def kite_shield(J, size=1.0, hand="L", emblem=True):
    e, w = J[f"elbow.{hand}"], J[f"wrist.{hand}"]
    c = e + (w - e) * 0.9 + Vector((0.0, -0.13, 0))   # centred over the fist so the hand hides behind it
    bm = bmesh.new()
    outline = [(0, 0.26), (0.13, 0.22), (0.17, 0.1), (0.15, -0.06), (0.09, -0.2), (0, -0.33),
               (-0.09, -0.2), (-0.15, -0.06), (-0.17, 0.1), (-0.13, 0.22)]
    f = bm.faces.new([bm.verts.new((x * size, 0, z * size)) for x, z in outline])
    bmesh.ops.solidify(bm, geom=[f], thickness=0.025)
    for v in bm.verts:   # gentle curve, bulging forward (-Y)
        v.co.y += (v.co.x ** 2) * 1.6
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    new_obj(xform(bm, Matrix.Translation(c)), "Shield", M_BODY if emblem else M_TRIM, "shield")   # crested: gold rim
    # inner field slightly sunk -> reads as a rim
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new((x * size * 0.84, 0, z * size * 0.86 - 0.01)) for x, z in outline])
    bmesh.ops.solidify(bm, geom=[f], thickness=0.012)
    for v in bm.verts: v.co.y += (v.co.x ** 2) * 1.6 - 0.018
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    new_obj(xform(bm, Matrix.Translation(c)), "ShieldField", M_TRIM if emblem else M_BODY, "shield")
    if not emblem: return c
    # raised cross, bent with the same curve as the shield so it sits ON the face (a flat bar floated off the edges)
    for nm, sx, sz, zc in (("CrossV", 0.035, 0.44, -0.03), ("CrossH", 0.24, 0.035, 0.09)):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.x - e.verts[1].co.x) > 0.5],
                                  cuts=10, use_grid_fill=True)
        xform(bm, Matrix.Translation((0, -0.03, zc * size)) @ Matrix.Diagonal((sx * size, 0.022, sz * size, 1)))
        for v in bm.verts: v.co.y += (v.co.x ** 2) * 1.6
        new_obj(xform(bm, Matrix.Translation(c)), nm, M_BODY, "shield")
    return c

def pedestal(r=0.55, h=0.17, style="low"):
    """Round, moulded statue base; follows root so the whole piece can slide / topple."""
    if style == "tall":   # classic turned chess base: wide foot, cove, bead, waisted neck, top collar
        u = h / 0.28
        prof = [(0, 0), (r, 0), (r, 0.025), (r * 0.97, 0.04), (r * 0.97, 0.06), (r * 0.9, 0.075), (r * 0.82, 0.1),
                (r * 0.74, 0.135), (r * 0.7, 0.17), (r * 0.72, 0.19), (r * 0.8, 0.205), (r * 0.8, 0.225),
                (r * 0.74, 0.24), (r * 0.76, 0.26), (r * 0.76, 0.275), (r * 0.72, 0.28), (0, 0.28)]
        prof = [(a, b * u) for a, b in prof]
    else:
        u = h / 0.15
        prof = [(0, 0), (r, 0), (r, 0.02 * u), (r * 0.975, 0.03 * u), (r * 0.975, 0.055 * u), (r * 0.93, 0.07 * u),
                (r * 0.905, 0.075 * u), (r * 0.89, 0.115 * u), (r * 0.92, 0.125 * u), (r * 0.925, 0.14 * u),
                (r * 0.9, 0.15 * u), (0, 0.15 * u)]
    lathe("Pedestal", prof, M_BODY, "root", 48)
    return h

# ---------------------------------------------------------------- pieces
DAGGER_L = 0.5   # blade length (human metres); tip = grip + (0.1 + DAGGER_L) along the bone

def sheath_frame(J, side):
    """Where the dagger for hand `side` rides on the belt: worn for a CROSS draw (user: "クロスで抜刀"), so the
    right hand's dagger hangs at the left hip and vice versa, hilts canted forward toward the drawing hand.
    The two sit at slightly different heights so the crossing forearms pass one above the other."""
    s = -1 if side == "L" else 1                         # +1: on the piece's left hip
    hilt = J["spine"] + Vector((s * 0.21, -0.06, 0.05 if side == "R" else -0.01))
    return hilt, Vector((s * 0.3, 0.45, -0.84)).normalized()

def scabbard(J, side, blade=None):
    hilt, dn = sheath_frame(J, side)
    a, b = hilt + dn * 0.09, hilt + dn * (0.12 + (blade or DAGGER_L))
    m = along(a, b) @ Matrix.Diagonal((1.0, 0.45, 1, 1))   # flattened: the blade's flats face out
    out = Vector((1 if side == "L" else -1, 0, 0))
    for nm, z0, z1, r0, r1, mat in (("Scabbard", 0.0, 1.0, 0.05, 0.034, M_BODY), ("Throat", 0.0, 0.08, 0.056, 0.056, M_TRIM),
                                    ("Chape", 0.88, 1.0, 0.04, 0.012, M_TRIM)):
        L = (b - a).length
        bm = lathe_bm([(0, z0 * L), (r0 + (r1 - r0) * z0, z0 * L), (r0 + (r1 - r0) * z1, z1 * L), (0, z1 * L)], 12)
        new_obj(xform(bm, m @ Matrix.Rotation(math.atan2(out.y, out.x), 4, 'Z')), f"{nm}{side}", mat, "hips")
    rod(f"Frog{side}", hilt + dn * 0.1 + Vector((0, 0, 0.0)), J["spine"] + Vector((-0.18 if side == "L" else 0.18, -0.02, 0.02)),
        0.014, 0.014, M_TRIM, "hips", 6)   # strap to the belt

def pawn_look(J):
    """Design sheet "ポーン（双剣）": the classic pawn silhouette - a smooth ball head with a small finial - on a
    duellist in a long flared coat with a scalloped capelet, all edged in gold."""
    n = J["neck"]
    hc = J["head"] + Vector((0, 0, 0.12))
    sphere("PawnHead", 0.155, hc, M_BODY, "head", seg=24)
    sphere("Finial", 0.032, hc + Vector((0, 0, 0.17)), M_BODY, "head", seg=12)
    lathe("FinialNeck", [(0, 0.135), (0.03, 0.135), (0.018, 0.155), (0, 0.155)], M_BODY, "head", 12, Matrix.Translation(hc))
    lathe("Collar", [(0.075, -0.03), (0.105, -0.03), (0.095, 0.06), (0.07, 0.07)], M_TRIM, "neck", 24, Matrix.Translation(n))
    # a hood (model sheet), thrown back: a soft cowl round the neck and the folded hood lying behind the head
    shell("Cowl", [(0.1, 0.07), (0.14, 0.02), (0.17, -0.05), (0.19, -0.1)], M_BODY, "neck", 28,
          Matrix.Translation(n) @ Matrix.Diagonal((1, 0.9, 1, 1)), thick=0.022)
    shell("Hood", [(0.0, 0.2), (0.09, 0.17), (0.15, 0.08), (0.16, -0.02), (0.14, -0.08)], M_BODY, "neck", 20,
          Matrix.Translation(n + Vector((0, 0.11, 0.02))) @ Matrix.Diagonal((0.9, 0.55, 0.85, 1)),
          a0=math.radians(20), a1=math.radians(160), thick=0.02)
    # capelet over the shoulders: a short cone with a gold scalloped edge
    cm = Matrix.Translation(n + Vector((0, 0.01, 0.0))) @ Matrix.Diagonal((1, 0.82, 1, 1))
    shell("Capelet", [(0.09, 0.02), (0.2, -0.06), (0.29, -0.17), (0.31, -0.22)], M_BODY, "chest", 32, cm, thick=0.016)
    for k in range(16):
        a = k / 16 * 2 * math.pi
        sphere(f"Scallop{k}", 0.034, n + Vector((0.305 * math.sin(a), -0.305 * 0.82 * math.cos(a) + 0.01, -0.225)), M_TRIM, "chest",
               scale=(1.0, 0.45, 0.7), rot=(0, 0, -a), seg=10)
    # long coat from the waist, flaring wide toward the hem (gold hem, gold front edges)
    top = J["spine"] - Vector((0, 0, 0.02))
    length = 0.7
    m = Matrix.Translation(top) @ Matrix.Diagonal((1, 0.86, 1, 1))
    prof = [(0.19, 0.0), (0.215, -0.12), (0.28, -0.36), (0.39, -length)]
    for o in (shell("Coat", prof, M_BODY, None, 40, m, a0=math.radians(-75), a1=math.radians(255), thick=0.015),
              shell("CoatHem", [(0.392, -length + 0.06), (0.397, -length + 0.005)], M_TRIM, None, 40, m,
                    a0=math.radians(-75), a1=math.radians(255), thick=0.017)):
        skirt_weights(o, top.z, top.z - length, 0.18)
    for side in (-1, 1):   # gold edging down the open front of the coat
        a = math.radians(-75 if side < 0 else 255)
        pts = [top + Vector((r * math.cos(a), r * 0.86 * math.sin(a), z)) for r, z in prof]
        for k in range(len(pts) - 1):
            o = rod(f"CoatEdge{side}{k}", pts[k], pts[k + 1], 0.016, 0.016, M_TRIM, None, 6)
            skirt_weights(o, top.z, top.z - length, 0.18)
    lathe("Belt", [(0, -0.03), (0.2, -0.03), (0.205, 0.03), (0, 0.03)], M_TRIM, "spine", 32, m)

def build_pawn():
    p = {"bulk": 1.0, "leg": 1.0, "head": 1.0, "base": 0.0}   # no pedestal: stands on the board
    J = skeleton(p)
    body = skin_body(J, p)
    pawn_look(J)
    cuirass(J, 1.0); pauldrons(J, 0.1); limb_armour(J, grip=("L", "R"))
    # a pair of long daggers (user: "ポーンは二つの短剣"), gold guards; each blade's bone runs along the blade
    d = Vector((0, -1, 0.15)).normalized()
    gR = sword(J, DAGGER_L, "R", "weapon", 0.75, 0.04)
    gL = sword(J, DAGGER_L, "L", "weapon.L", 0.75, 0.04)
    extra = {"weapon": (gR, gR + d * 0.2, "hand.R"), "weapon.L": (gL, gL + d * 0.2, "hand.L")}
    # worn sheathed on the belt and drawn for the fight (user: "短剣腰から出して戦ってほしい"):
    # sheath.X = the sheathed dagger's frame (head = grip, Y = blade), hilt.X = where the wrist rests on the hilt
    for side in ("L", "R"):
        scabbard(J, side)
        hilt, dn = sheath_frame(J, side)
        hl = (J[f"handtip.{side}"] - J[f"wrist.{side}"]).length * 0.7   # wrist -> fist centre
        to_sh = J[f"shoulder.{side}"] - hilt; to_sh.z = 0; to_sh.normalize()   # reached across the body
        wr = hilt + to_sh * hl * 0.85 + Vector((0, 0.03, hl * 0.4))   # wrist on the drawing hand's side of the hilt
        extra[f"sheath.{side}"] = (hilt, hilt + dn * 0.2, "hips")
        extra[f"hilt.{side}"] = (wr, wr + Vector((0, 0, 0.08)), "hips")
    return J, body, extra, 0.6   # ~1.2 squares tall; idle silhouette stays inside one square

PIECES = {"Pawn": build_pawn}

# ---------------------------------------------------------------- rig + assemble
def make_rig(name, J, extra, bones=None):
    arm = bpy.data.armatures.new(name + "_Rig")
    rig = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(rig)
    arm.display_type = 'STICK'
    for o in bpy.context.selected_objects: o.select_set(False)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bn, h, t, par in (bones or BONES):
        eb = arm.edit_bones.new(bn)
        eb.head = J[h]
        eb.tail = J[t] if t else J[h] + Vector((0, 0.25, 0))
        if par: eb.parent = arm.edit_bones[par]
        eb.use_deform = True
    for bn, (h, t, par) in extra.items():
        eb = arm.edit_bones.new(bn)
        eb.head, eb.tail = h, t
        eb.parent = arm.edit_bones[par]
    for eb in arm.edit_bones:   # local Z forward(-Y) so local X is the hinge axis for limbs/spine
        if eb.name != "root": eb.align_roll(Vector((0, -1, 0)))
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig

def assemble(name):
    """A piece builder returns either (J, body, extra, scale) for a single humanoid, or a dict with
    J / extra / scale / bones and bodies = [(mesh, names of the bones allowed to deform it), ...]
    (the knight: horse body weighted only to horse bones, rider only to rider bones)."""
    PARTS.clear(); AUTO.clear()
    res = PIECES[name]()
    if isinstance(res, tuple):
        J, body, extra, scale = res
        res = dict(J=J, extra=extra, scale=scale, bones=BONES, bodies=[(body, None)])
    bodies = res["bodies"]
    if AUTO:
        objs = [bodies[0][0]] + AUTO
        with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, object=objs[0]):
            bpy.ops.object.join()
    rig = make_rig(name, res["J"], res["extra"], res["bones"])
    for mesh, allowed in bodies:   # auto weights per organic body, restricted to its own bones
        props = set(res["extra"])   # weapon / shield / orb / sheath ... bones carry rigid parts only: never skin
        for b in rig.data.bones: b.use_deform = (allowed is None or b.name in allowed) and b.name not in props
        for o in bpy.context.selected_objects: o.select_set(False)
        mesh.select_set(True); rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        fb = "hips" if allowed is None or "hips" in allowed else next(iter(allowed))
        grp = mesh.vertex_groups.get(fb) or mesh.vertex_groups.new(name=fb)
        lost = [v.index for v in mesh.data.vertices if not any(g.weight > 1e-4 for g in v.groups)]
        if lost: grp.add(lost, 1.0, 'REPLACE'); print("fallback-weighted", len(lost), "verts to", fb)
    for b in rig.data.bones: b.use_deform = True
    body = bodies[0][0]
    # join the other bodies and the rigid parts (vertex groups merge by name)
    objs = [body] + [m for m, _ in bodies[1:]] + PARTS
    with bpy.context.temp_override(active_object=body, selected_editable_objects=objs, object=body):
        bpy.ops.object.join()
    for m in body.modifiers:
        if m.type == 'ARMATURE': m.object = rig
    arms = [m for m in body.modifiers if m.type == 'ARMATURE']
    for m in arms[1:]: body.modifiers.remove(m)
    body.name = body.data.name = name + "_Mesh"
    for poly in body.data.polygons: poly.use_smooth = True
    body.data.set_sharp_from_angle(angle=math.radians(40))
    # scale to board units and apply
    rig["piece_scale"] = res["scale"]
    rig.scale = (res["scale"],) * 3
    for o in bpy.context.selected_objects: o.select_set(False)
    rig.select_set(True); body.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return rig, body

def build(names=None):
    clear_scene(); materials()
    out = {}
    for i, n in enumerate(names or PIECES):
        rig, mesh = assemble(n)
        rig.location.x = i * 0.9
        out[n] = (rig, mesh)
        print(n, len(mesh.data.polygons), "faces")
    return out

if __name__ == "__main__":
    build()
