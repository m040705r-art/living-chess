# The stage around the board: a moonlit ruin (user: "チェスの周りの舞台も変えたい" -> 月夜の廃墟・遺跡).
# Run inside Blender (builds into its own scene "Stage", seeded, so it rebuilds identically):
#   exec(open(CHESS + "/BlenderSource/stage.py", encoding="utf-8").read())
# Exports Assets/Chess/Art/Models/Stage.fbx (Unity) and WebPreview/models/Stage.glb.
# Centred on the board centre; the board's rim top sits at z = -0.01, the ruin floor at z = GROUND.
# One mesh, four materials (Ruin, RuinFloor, Earth, Moss) -> a handful of draw calls for the iGPU.
import os as _os, bpy as _bpy
# the repository root: $CHESS_ROOT, else the folder above the open .blend / this script (no machine paths in the repo)
CHESS = (_os.environ.get("CHESS_ROOT") or (_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))) if "__file__" in globals() else "")
         or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)) or ".").replace("\\", "/")

def scrub_user(path):
    """FBX files record the path they were written to: blank out the home folder's name before it is committed."""
    u = _os.path.basename(_os.path.expanduser("~")).encode()
    b = open(path, "rb").read()
    if u and u in b: open(path, "wb").write(b.replace(u, b"x" * len(u)))   # same length: the binary FBX stays valid

import bpy, bmesh, math, random
from mathutils import Vector, Matrix

OUT_FBX = CHESS + "/Assets/Chess/Art/Models/Stage.fbx"
OUT_GLB = CHESS + "/WebPreview/models/Stage.glb"
GROUND = -0.5
MATS = {"Ruin": (0.42, 0.43, 0.46), "RuinFloor": (0.30, 0.31, 0.33), "Earth": (0.06, 0.065, 0.06), "Moss": (0.16, 0.22, 0.14)}
MI = {n: i for i, n in enumerate(MATS)}
rnd = random.Random(7)

bm = bmesh.new()

def put(geom_verts, mat):
    for f in {f for v in geom_verts for f in v.link_faces}: f.material_index = MI[mat]

def block(c, size, mat="Ruin", rot=(0, 0, 0), chip=0.0):
    """A box centred on c; chip > 0 knocks the corners about a little so nothing reads as a clean primitive."""
    r = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    m = Matrix.Translation(Vector(c)) @ (Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X')) \
        @ Matrix.Diagonal((*size, 1))
    for v in r:
        v.co = m @ (v.co + Vector((rnd.uniform(-chip, chip), rnd.uniform(-chip, chip), rnd.uniform(-chip, chip))))
    put(r, mat); return r

def drum(c, radius, h, mat="Ruin", seg=12, axis=None, broken=0.0, flute=0.0):
    """A column drum standing on c (or lying along axis); broken > 0 shatters its top ring."""
    vs = []
    for k in (0, 1):
        ring = []
        for i in range(seg):
            a = i / seg * math.tau
            rr = radius * (1 - (flute if i % 2 else 0))
            z = h * k + (rnd.uniform(-broken, broken * 0.4) if k and broken else 0)
            ring.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, z)))
        vs.append(ring)
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((vs[0][i], vs[0][j], vs[1][j], vs[1][i]))
    bm.faces.new(list(reversed(vs[0]))); bm.faces.new(vs[1])
    allv = vs[0] + vs[1]
    if axis is not None:   # lying down: rotate about the axis' perpendicular
        rot = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized()).to_matrix().to_4x4()
        for v in allv: v.co = rot @ v.co
    for v in allv: v.co += Vector(c)
    put(allv, mat); return allv

def rock(c, s, mat="Ruin"):
    r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)["verts"]
    sq = Vector((rnd.uniform(0.7, 1.3), rnd.uniform(0.7, 1.3), rnd.uniform(0.4, 0.8)))
    for v in r:
        v.co = Vector(c) + Vector((v.co.x * sq.x, v.co.y * sq.y, v.co.z * sq.z)) * s * rnd.uniform(0.8, 1.15)
    put(r, mat); return r

# ---- the dais the board rests on: two stepped tiers of big slabs, worn and chipped at the edges
def tier(half, z0, z1, n):
    step = 2 * half / n
    for i in range(n):
        for j in range(n):
            if 0 < i < n - 1 and 0 < j < n - 1: continue   # only the ring of edge slabs; the core is one block
            if rnd.random() < 0.06: continue                 # a missing slab
            cx, cy = -half + step * (i + 0.5), -half + step * (j + 0.5)
            dz = rnd.uniform(-0.03, 0.0)
            block((cx, cy, (z0 + z1) / 2 + dz), (step - 0.03, step - 0.03, z1 - z0), "Ruin", (0, 0, rnd.uniform(-0.03, 0.03)), chip=0.03)
    core = half - step
    block((0, 0, (z0 + z1) / 2), (2 * core, 2 * core, z1 - z0), "Ruin")
tier(5.0, -0.3, -0.17, 8)
tier(5.75, GROUND, -0.3, 9)

# ---- the floor of the ruin: flagstones, sunken, tilted and some gone (earth shows through), moss in the gaps
block((0, 0, GROUND - 0.06), (60, 60, 0.1), "Earth")
S = 1.35
for i in range(-12, 13):
    for j in range(-12, 13):
        cx, cy = i * S + (j % 2) * S * 0.5, j * S
        d = math.hypot(cx, cy)
        if max(abs(cx), abs(cy)) < 6.3 or d > 16: continue
        if rnd.random() < 0.12 + max(0, d - 10) * 0.05: continue   # thinner towards the dark edges
        w = S - rnd.uniform(0.04, 0.12)
        block((cx, cy, GROUND - 0.03 + rnd.uniform(-0.03, 0.02)), (w, w * rnd.uniform(0.85, 1.0), 0.08), "RuinFloor",
              (rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), rnd.uniform(-0.06, 0.06)), chip=0.02)
for _ in range(90):   # moss tufts in the cracks
    a, d = rnd.uniform(0, math.tau), rnd.uniform(6.2, 13)
    rock((math.cos(a) * d, math.sin(a) * d, GROUND + 0.01), rnd.uniform(0.12, 0.3), "Moss")

# ---- a ring of columns: most broken off, two still carrying a cracked lintel
COL_R, N_COL = 8.4, 10
cols = []
for k in range(N_COL):
    a = k / N_COL * math.tau + math.pi / N_COL
    x, y = math.cos(a) * COL_R, math.sin(a) * COL_R
    intact = k in (2, 3)
    h = 4.6 if intact else rnd.choice([0.7, 1.3, 2.1, 2.9, 3.6])
    block((x, y, GROUND + 0.18), (1.15, 1.15, 0.36), "Ruin", (0, 0, a), chip=0.03)   # plinth
    drum((x, y, GROUND + 0.36), 0.42, 0.22, "Ruin", seg=16)                       # torus-ish base
    drum((x, y, GROUND + 0.58), 0.36, h, "Ruin", seg=16, broken=0 if intact else 0.35, flute=0.06)
    if intact: block((x, y, GROUND + 0.58 + h + 0.15), (1.05, 1.05, 0.3), "Ruin", (0, 0, a), chip=0.02)   # capital
    cols.append((x, y, a, h, intact))
    for _ in range(rnd.randint(2, 5)):   # what fell off it lies at its foot
        ra, rd = rnd.uniform(0, math.tau), rnd.uniform(0.7, 1.8)
        rock((x + math.cos(ra) * rd, y + math.sin(ra) * rd, GROUND + 0.05), rnd.uniform(0.12, 0.32))
(x2, y2, a2, h2, _), (x3, y3, *_rest) = cols[2], cols[3]
mid = Vector(((x2 + x3) / 2, (y2 + y3) / 2, GROUND + 0.58 + h2 + 0.5))
span = Vector((x3 - x2, y3 - y2, 0))
block(mid, (span.length + 1.0, 0.8, 0.4), "Ruin", (0, 0, math.atan2(span.y, span.x)), chip=0.04)   # lintel
for k in (6, 8):   # fallen drums from the broken ones, lying across the floor
    x, y, a, *_ = cols[k]
    ax = Vector((math.cos(a + 1.9), math.sin(a + 1.9), 0))
    for n in range(3):
        drum((x + ax.x * (1.2 + n * 0.85), y + ax.y * (1.2 + n * 0.85), GROUND + 0.36), 0.36, 0.8, "Ruin", seg=16, axis=ax, flute=0.06)

# ---- a half-fallen arch behind the board (the camera sees it through the columns)
ARCH_A = math.radians(-60)
ac = Vector((math.cos(ARCH_A), math.sin(ARCH_A), 0)) * 11.5
tang = Vector((-math.sin(ARCH_A), math.cos(ARCH_A), 0))
SPAN, PIER_H = 1.8, 3.4
for s in (-1, 1):
    p = ac + tang * s * (SPAN + 0.45)
    for n in range(5):   # pier of stacked blocks
        block((p.x, p.y, GROUND + 0.35 + n * 0.68), (0.95, 1.0, 0.66), "Ruin", (0, 0, ARCH_A + rnd.uniform(-0.04, 0.04)), chip=0.03)
for n in range(11):      # voussoirs; the right half has broken away
    t = n / 10 * math.pi
    if n >= 7: continue
    pos = ac + tang * (-math.cos(t) * (SPAN + 0.45)) + Vector((0, 0, GROUND + PIER_H + math.sin(t) * (SPAN + 0.45)))
    block(pos, (0.55, 1.0, 0.6), "Ruin", (0, t - math.pi / 2, ARCH_A + math.pi / 2), chip=0.02)   # local z radial
for n in range(4):
    rock(ac + tang * rnd.uniform(0.8, 2.6) + Vector((rnd.uniform(-0.8, 0.8), 0, GROUND + 0.1)), rnd.uniform(0.2, 0.4))

# ---- broken walls further out, half-swallowed by the dark
for k in range(7):
    a = rnd.uniform(0, math.tau)
    if abs((a - ARCH_A + math.pi) % math.tau - math.pi) < 0.5: continue
    c = Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(12.5, 14)
    t = Vector((-math.sin(a), math.cos(a), 0))
    n_long = rnd.randint(3, 6)
    for i in range(n_long):
        rows = rnd.randint(1, 4)
        for r in range(rows):
            block(c + t * (i * 0.95 + (r % 2) * 0.45) + Vector((0, 0, GROUND + 0.25 + r * 0.5)), (0.92, 0.6, 0.48), "Ruin", (0, 0, a + math.pi / 2), chip=0.04)

# ---- four braziers off the dais corners, replacing the candles (the fire and its light live in the engines)
BRAZIERS = [(-6.1, -6.1), (6.1, -6.1), (-6.1, 6.1), (6.1, 6.1)]
for (x, y) in BRAZIERS:
    block((x, y, GROUND + 0.12), (0.6, 0.6, 0.24), "Ruin", chip=0.02)
    drum((x, y, GROUND + 0.24), 0.14, 0.75, "Ruin", seg=10)
    bowl = []
    for k, (rr, z) in enumerate(((0.12, 0.99), (0.36, 1.12), (0.42, 1.24))):
        ring = [bm.verts.new((x + math.cos(i / 12 * math.tau) * rr, y + math.sin(i / 12 * math.tau) * rr, GROUND + z)) for i in range(12)]
        bowl.append(ring)
    for k in range(2):
        for i in range(12):
            j = (i + 1) % 12
            bm.faces.new((bowl[k][i], bowl[k][j], bowl[k + 1][j], bowl[k + 1][i]))
    bm.faces.new(list(reversed(bowl[0])))
    coals = bm.verts.new((x, y, GROUND + 1.16))
    for i in range(12): bm.faces.new((bowl[2][i], bowl[2][(i + 1) % 12], coals))
    put(sum(bowl, []) + [coals], "Ruin")

# ---- into its own scene and out to the engines
sc = bpy.data.scenes.get("Stage") or bpy.data.scenes.new("Stage")
for o in list(sc.collection.objects): bpy.data.objects.remove(o, do_unlink=True)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bmesh.ops.triangulate(bm, faces=bm.faces[:])   # the shattered column tops are non-planar n-gons (Unity drops those)
me = bpy.data.meshes.get("Stage") or bpy.data.meshes.new("Stage")
me.materials.clear()   # the slots exist before to_mesh, or every material index is clamped to 0
for n, col in MATS.items():
    m = bpy.data.materials.get(n) or bpy.data.materials.new(n)
    m.use_nodes = True
    bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*col, 1); bsdf.inputs["Roughness"].default_value = 0.85
    me.materials.append(m)
bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = False
ob = bpy.data.objects.new("Stage", me)
sc.collection.objects.link(ob)
bpy.app.driver_namespace["stage_tris"] = sum(len(p.vertices) - 2 for p in me.polygons)
win = bpy.context.window; prev = win.scene
for o in prev.objects: o.select_set(False)   # the pieces' scene: nothing of it may ride along
win.scene = sc
for o in sc.objects: o.select_set(False)
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=OUT_FBX, use_selection=True, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                         axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', object_types={'MESH'})
scrub_user(OUT_FBX)
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True, use_active_scene=True, export_yup=True, export_animations=False)
win.scene = prev
