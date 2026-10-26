# The stage around the board: a sunset colosseum (user's arena sheet: a round marble arena floor with the board
# inlaid, a parapet of fire bowls, eagles and red eagle banners, tiers packed with a crowd, a two-storey arcade
# with flags on top, the imperial box with a red canopy and two lions, golden low sun, mountains far away).
# Replaces the moonlit ruin (stage.py, kept for reference).
# Run inside Blender (builds into its own scene "Arena", seeded, so it rebuilds identically):
#   exec(open(CHESS + "/BlenderSource/arena.py", encoding="utf-8").read())
# Exports Assets/Chess/Art/Models/Arena.fbx (Unity) and WebPreview/models/Arena.glb.
# Centred on the board centre (board top z = 0, rim top -0.01). One mesh; colour is in vertex colours and the
# material slots only pick the shading: Marble (stone noise), Gold, Cloth (sways), Crowd (bobs), Fire (flickers),
# Dark (shadowed openings). Vertex alpha = how much a vertex may move (cloth hem, crowd heads, flame tips).
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

OUT_FBX = CHESS + "/Assets/Chess/Art/Models/Arena.fbx"
OUT_GLB = CHESS + "/WebPreview/models/Arena.glb"
MATS = ["Marble", "Gold", "Cloth", "Crowd", "Fire", "Dark"]
MI = {n: i for i, n in enumerate(MATS)}
rnd = random.Random(11)

MARBLE = (0.86, 0.82, 0.74); MARBLE_D = (0.70, 0.65, 0.57); SAND = (0.78, 0.68, 0.52)
GOLD = (0.95, 0.72, 0.32); RED = (0.62, 0.06, 0.05); DARK = (0.10, 0.07, 0.06)

R_DAIS, R_FLOOR, R_WALL = 6.4, 10.6, 11.2          # board dais, arena floor, parapet
R_STAND0, R_STAND1, N_TIER = 11.6, 19.0, 9          # crowd tiers
H_WALL = 1.4
R_ARCADE, H_ARCADE = 19.6, 15.0
BOX_A = math.radians(90)                              # the imperial box faces the board from +Y (Blender)

bm = bmesh.new()
col = bm.loops.layers.color.new("Col")

def paint(faces, mat, rgb, a=0.0, a_top=None, ztop=None):
    """Material + vertex colour; a_top: alpha for vertices above ztop (moving parts)."""
    for f in faces:
        f.material_index = MI[mat]
        for l in f.loops:
            al = a_top if (a_top is not None and l.vert.co.z > ztop) else a
            l[col] = (*rgb, al)

def faces_of(verts): return list({f for v in verts for f in v.link_faces})
def jit(c, k):   # one brightness factor for all channels: per-channel jitter turned marble pink and green
    j = 1 + rnd.uniform(-k, k)
    return tuple(min(1, max(0, x * j)) for x in c)

def box(c, size, mat, rgb, rot_z=0.0, tilt=(0, 0)):
    vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    m = Matrix.Translation(Vector(c)) @ Matrix.Rotation(rot_z, 4, 'Z') @ Matrix.Rotation(tilt[1], 4, 'Y') @ Matrix.Rotation(tilt[0], 4, 'X') @ Matrix.Diagonal((*size, 1))
    for v in vs: v.co = m @ v.co
    fs = faces_of(vs); paint(fs, mat, rgb); return vs

def cyl(c, r0, r1, h, seg, mat, rgb, cap=True):
    """A turned shape from radius r0 (bottom) to r1 (top)."""
    b = [bm.verts.new((c[0] + math.cos(i / seg * math.tau) * r0, c[1] + math.sin(i / seg * math.tau) * r0, c[2])) for i in range(seg)]
    t = [bm.verts.new((c[0] + math.cos(i / seg * math.tau) * r1, c[1] + math.sin(i / seg * math.tau) * r1, c[2] + h)) for i in range(seg)]
    fs = [bm.faces.new((b[i], b[(i + 1) % seg], t[(i + 1) % seg], t[i])) for i in range(seg)]
    if cap: fs += [bm.faces.new(list(reversed(b))), bm.faces.new(t)]
    paint(fs, mat, rgb); return b + t

def ring(r0, r1, z0, z1, seg, mat, rgb, a0=0.0, a1=math.tau):
    """An annulus band (a step / a wall) between radii r0 < r1 from z0 to z1, angles a0..a1."""
    n = seg; pts = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        cs, sn = math.cos(a), math.sin(a)
        pts.append([bm.verts.new((cs * r, sn * r, z)) for r, z in ((r0, z0), (r0, z1), (r1, z1), (r1, z0))])
    fs = []
    for i in range(n):
        p, q = pts[i], pts[i + 1]
        for k in range(3 if r0 > 0.01 else 2):
            fs.append(bm.faces.new((p[k], q[k], q[k + 1], p[k + 1])))
        fs.append(bm.faces.new((p[3], q[3], q[0], p[0])))
    if abs(a1 - a0 - math.tau) > 1e-6:
        fs.append(bm.faces.new(list(reversed(pts[0])))); fs.append(bm.faces.new(pts[-1]))
    paint(fs, mat, rgb); return fs

def flame(c, s):
    """Three crossed tongues of fire; tips may sway (alpha 1)."""
    out = []
    for k in range(3):
        a = k / 3 * math.pi
        dx, dy = math.cos(a) * s * 0.5, math.sin(a) * s * 0.5
        v = [bm.verts.new((c[0] - dx, c[1] - dy, c[2])), bm.verts.new((c[0] + dx, c[1] + dy, c[2])),
             bm.verts.new((c[0] + dx * 0.4, c[1] + dy * 0.4, c[2] + s * 1.1)), bm.verts.new((c[0], c[1], c[2] + s * 2.0)),
             bm.verts.new((c[0] - dx * 0.4, c[1] - dy * 0.4, c[2] + s * 1.1))]
        out.append(bm.faces.new(v))
    paint(out, "Fire", (1.0, 0.62, 0.22), a=0.0, a_top=1.0, ztop=c[2] + s * 0.3)

def fire_bowl(c, s=1.0, pedestal=1.1):
    x, y, z = c
    box((x, y, z + pedestal / 2), (0.55 * s, 0.55 * s, pedestal), "Marble", MARBLE)
    box((x, y, z + pedestal + 0.04), (0.68 * s, 0.68 * s, 0.08), "Marble", MARBLE_D)
    cyl((x, y, z + pedestal + 0.08), 0.1 * s, 0.1 * s, 0.12 * s, 8, "Gold", GOLD)
    cyl((x, y, z + pedestal + 0.2 * s), 0.12 * s, 0.38 * s, 0.22 * s, 12, "Gold", GOLD)
    flame((x, y, z + pedestal + 0.36 * s), 0.24 * s)
    return (x, y, z + pedestal + 0.6 * s)

def frame(x, y, z, face_a):
    """Local placement: fwd along face_a, side to the left of it, up."""
    fx, fy = math.cos(face_a), math.sin(face_a)
    return lambda fwd, side=0.0, up=0.0: (x + fx * fwd - fy * side, y + fy * fwd + fx * side, z + up)

def eagle(c, s, face_a):
    """A gilded eagle on a ball, wings raised (sheet: eagles on the parapet and over the imperial box).
    Every part overlaps the one it grows from, and the ball sits on the surface at c."""
    P = frame(*c, face_a)
    cyl(P(0, 0, 0), 0.09 * s, 0.09 * s, 0.05 * s, 8, "Gold", GOLD)                          # foot plate
    cyl(P(0, 0, 0.04 * s), 0.12 * s, 0.07 * s, 0.14 * s, 8, "Gold", GOLD)                   # the ball it grips
    box(P(0.0, 0, 0.36 * s), (0.2 * s, 0.24 * s, 0.46 * s), "Gold", GOLD, face_a, tilt=(0, -0.15))   # body
    box(P(-0.1 * s, 0, 0.14 * s), (0.22 * s, 0.16 * s, 0.06 * s), "Gold", GOLD, face_a, tilt=(0, 0.5))   # tail fan
    box(P(0.05 * s, 0, 0.66 * s), (0.17 * s, 0.14 * s, 0.17 * s), "Gold", GOLD, face_a)                 # head
    box(P(0.16 * s, 0, 0.63 * s), (0.1 * s, 0.06 * s, 0.06 * s), "Gold", GOLD, face_a, tilt=(0, 0.6))   # hooked beak
    for sd in (-1, 1):
        for k, (ln, wd, lift) in enumerate(((0.36, 0.26, 0.55), (0.32, 0.2, 1.05))):    # inner and outer wing
            root = (0.1 + 0.24 * k) * s
            ang = lift
            cy = root + math.cos(ang) * ln * s * 0.5 - (0.06 * s if k else 0)
            cz = 0.5 * s + (math.sin(0.55) * 0.36 * s * k) + math.sin(ang) * ln * s * 0.5
            box(P(-0.02 * s, sd * cy, cz), (0.05 * s, ln * s, wd * s), "Gold", GOLD, face_a, tilt=(sd * ang, 0))

def banner(c, w, h, face_a, emblem=True, gap=0.1):
    """A hanging red banner, facing angle face_a, hung gap in front of the wall at c (top centre) on a gold rod
    fixed into the wall. Only the lower part sways, and gently, so it never swings back into the wall; the
    eagle is painted flat on the cloth (a hair in front of it) and moves exactly with it."""
    x, y, z = c
    nx, ny = math.cos(face_a), math.sin(face_a)
    tx, ty = -ny, nx
    cols, rows = 3, 5
    ox, oy = x + nx * gap, y + ny * gap
    sway = lambda zz: 0.55 * max(0.0, min(1.0, (z - zz) / h)) ** 1.5
    grid = [[bm.verts.new((ox + tx * (i / cols - 0.5) * w, oy + ty * (i / cols - 0.5) * w, z - j / rows * h)) for i in range(cols + 1)] for j in range(rows + 1)]
    tip = bm.verts.new((ox, oy, z - h * 1.12))
    fs = [bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1])) for j in range(rows) for i in range(cols)]
    fs.append(bm.faces.new((grid[rows][0], tip, grid[rows][cols])))
    for f in fs:
        f.material_index = MI["Cloth"]
        for l in f.loops: l[col] = (*RED, sway(l.vert.co.z))
    # the rod: along the banner's top edge, running back into the wall at both ends
    box((ox, oy, z + 0.02), (0.05, w + 0.16, 0.05), "Gold", GOLD, face_a)
    for sd in (-0.5, 0.5):
        box((x + nx * gap * 0.5 + tx * sd * (w + 0.1), y + ny * gap * 0.5 + ty * sd * (w + 0.1), z + 0.02), (gap + 0.06, 0.04, 0.04), "Gold", GOLD, face_a)
    if emblem:
        ex, ey, ez = ox + nx * 0.006, oy + ny * 0.006, z - h * 0.45
        def quad(pts):
            vs = [bm.verts.new((ex + tx * u, ey + ty * u, ez + v)) for u, v in pts]
            f = bm.faces.new(vs); f.material_index = MI["Gold"]
            for l in f.loops: l[col] = (*GOLD, sway(l.vert.co.z))
        k = w * 0.42
        quad([(-0.12 * k, -0.5 * k), (0.12 * k, -0.5 * k), (0.12 * k, 0.35 * k), (-0.12 * k, 0.35 * k)])      # body
        quad([(-0.1 * k, 0.35 * k), (0.1 * k, 0.35 * k), (0.08 * k, 0.6 * k), (-0.08 * k, 0.6 * k)])           # head
        for sd in (-1, 1):
            quad([(0.1 * k * sd, 0.25 * k), (0.95 * k * sd, 0.7 * k), (0.85 * k * sd, 0.3 * k), (0.1 * k * sd, -0.15 * k)][::sd])   # wings
        quad([(-0.3 * k, -0.5 * k), (0.3 * k, -0.5 * k), (0.15 * k, -0.75 * k), (-0.15 * k, -0.75 * k)])      # tail

TUNICS = [(0.55, 0.12, 0.08), (0.80, 0.74, 0.62), (0.45, 0.32, 0.2), (0.25, 0.3, 0.45), (0.7, 0.52, 0.2),
          (0.35, 0.36, 0.3), (0.9, 0.86, 0.78), (0.3, 0.42, 0.28), (0.6, 0.35, 0.45)]
SKINS = [(0.85, 0.62, 0.45), (0.7, 0.48, 0.32), (0.5, 0.33, 0.22), (0.92, 0.72, 0.56)]
HAIRS = [(0.12, 0.08, 0.05), (0.25, 0.15, 0.08), (0.05, 0.04, 0.04), (0.55, 0.5, 0.45), (0.6, 0.42, 0.2)]

def person(c, face_a, h, legs=True, noble=False):
    """A seated spectator, ~40 tris: thighs, a tapered torso, a head with hair (or a straw hat / a legionary's
    helmet with a red crest), and arms posed one of four ways (resting, one fist up, both up, clapping).
    Vertex alpha: torso 0.35, head and arms 1 (the crowd wave lifts them)."""
    x, y, z = c
    face_a += rnd.uniform(-0.15, 0.15)
    P = frame(x, y, z, face_a)
    tunic = (0.92, 0.9, 0.84) if noble else jit(rnd.choice(TUNICS), 0.12)
    skin, hair = rnd.choice(SKINS), rnd.choice(HAIRS)
    if legs:
        vs = box(P(0.16 * h, 0, 0.09 * h), (0.36 * h, 0.3 * h, 0.18 * h), "Crowd", tuple(v * 0.7 for v in tunic), face_a)
        paint(faces_of(vs), "Crowd", tuple(v * 0.7 for v in tunic), a=0.2)
    tv = box(P(0, 0, 0.36 * h), (0.24 * h, 0.34 * h, 0.5 * h), "Crowd", tunic, face_a)
    top = [v for v in tv if v.co.z > z + 0.36 * h]   # taper to the shoulders
    ctr = sum((v.co for v in top), Vector()) / 4
    for v in top: v.co = ctr + (v.co - ctr) * 0.8
    paint(faces_of(tv), "Crowd", tunic, a=0.35)
    if noble:   # a purple stripe down the front of the toga
        sv = box(P(0.125 * h, 0.05 * h, 0.36 * h), (0.01 * h, 0.06 * h, 0.5 * h), "Crowd", (0.35, 0.1, 0.35), face_a, tilt=(0.3, 0))
        paint(faces_of(sv), "Crowd", (0.35, 0.1, 0.35), a=0.35)
    hv = box(P(0, 0, 0.73 * h), (0.2 * h, 0.19 * h, 0.24 * h), "Crowd", skin, face_a)
    fwd = Vector((math.cos(face_a), math.sin(face_a), 0))
    kind = rnd.random()
    for f in faces_of(hv):
        ctr_f = f.calc_center_median()
        hairy = ctr_f.z > z + 0.84 * h or (ctr_f - Vector(P(0, 0, 0.73 * h))).dot(fwd) < -0.09 * h
        for l in f.loops: l[col] = (*(hair if hairy else skin), 1.0)
        f.material_index = MI["Crowd"]
    if kind < 0.08:     # a legionary: steel helmet with a red crest
        for vs, rgb in ((box(P(0, 0, 0.86 * h), (0.23 * h, 0.22 * h, 0.06 * h), "Crowd", (0.55, 0.55, 0.58), face_a), (0.55, 0.55, 0.58)),
                        (box(P(0, 0, 0.93 * h), (0.24 * h, 0.04 * h, 0.1 * h), "Crowd", (0.7, 0.08, 0.06), face_a), (0.7, 0.08, 0.06))):
            paint(faces_of(vs), "Crowd", rgb, a=1.0)
    elif kind < 0.16:   # a straw hat against the sun
        vs = box(P(0, 0, 0.86 * h), (0.36 * h, 0.36 * h, 0.03 * h), "Crowd", (0.85, 0.72, 0.42), face_a + 0.785)
        paint(faces_of(vs), "Crowd", (0.85, 0.72, 0.42), a=1.0)
    pose = rnd.random()
    arms = []
    if pose < 0.25:      # one fist punched up
        sd = rnd.choice((-1, 1))
        arms.append((P(0, sd * 0.2 * h, 0.78 * h), (0.08 * h, 0.08 * h, 0.4 * h), (-sd * 0.25, 0)))
    elif pose < 0.4:     # both arms up in a V
        for sd in (-1, 1): arms.append((P(0, sd * 0.22 * h, 0.76 * h), (0.08 * h, 0.08 * h, 0.4 * h), (-sd * 0.4, 0)))
    elif pose < 0.62:    # clapping: forearms out in front
        for sd in (-1, 1): arms.append((P(0.15 * h, sd * 0.07 * h, 0.48 * h), (0.3 * h, 0.07 * h, 0.07 * h), (0, -0.4)))
    for (cc, sz, tl) in arms:
        vs = box(cc, sz, "Crowd", skin, face_a, tilt=tl)
        paint(faces_of(vs), "Crowd", skin, a=1.0)

def lion(c, s, face_a):
    """A seated marble lion on its plinth (sheet: two lions flanking the imperial stair). The body is a skin-
    modifier sculpture (spine, folded hind legs, straight forelegs, tail curled round the paws) smoothed once,
    the mane a cluster of rough lumps round the head and neck; all of it is merged into the arena mesh."""
    P = frame(*c, face_a)
    box(P(0, 0, 0.35 * s), (1.5 * s, 0.9 * s, 0.7 * s), "Marble", MARBLE, face_a)                 # plinth
    box(P(0, 0, 0.73 * s), (1.6 * s, 1.0 * s, 0.06 * s), "Marble", MARBLE_D, face_a)              # its cap
    base_z = 0.76 * s
    k = 0.78 * s   # sculpture scale
    nodes = {   # name: ((fwd, side, up) in sculpture units, radius)
        "hip": ((-0.38, 0, 0.36), 0.3), "belly": ((-0.1, 0, 0.52), 0.3), "chest": ((0.18, 0, 0.8), 0.35),
        "neck": ((0.3, 0, 1.1), 0.27), "head": ((0.42, 0, 1.32), 0.25), "snout": ((0.66, 0, 1.24), 0.15),
        "jaw": ((0.6, 0, 1.12), 0.11),
        "tailA": ((-0.66, 0, 0.18), 0.05), "tailB": ((-0.7, 0.3, 0.06), 0.04), "tailC": ((-0.3, 0.48, 0.05), 0.035),
    }
    edges = [("hip", "belly"), ("belly", "chest"), ("chest", "neck"), ("neck", "head"), ("head", "snout"), ("head", "jaw"),
             ("hip", "tailA"), ("tailA", "tailB"), ("tailB", "tailC")]
    for sd, nm in ((1, "L"), (-1, "R")):
        nodes.update({f"sh{nm}": ((0.2, sd * 0.2, 0.72), 0.15), f"el{nm}": ((0.3, sd * 0.21, 0.38), 0.12),
                      f"pw{nm}": ((0.36, sd * 0.21, 0.06), 0.12), f"to{nm}": ((0.54, sd * 0.21, 0.06), 0.1),
                      f"th{nm}": ((-0.36, sd * 0.26, 0.38), 0.2), f"kn{nm}": ((-0.06, sd * 0.33, 0.24), 0.13),
                      f"an{nm}": ((-0.46, sd * 0.3, 0.08), 0.08), f"hp{nm}": ((-0.12, sd * 0.28, 0.05), 0.09)})
        edges += [("chest", f"sh{nm}"), (f"sh{nm}", f"el{nm}"), (f"el{nm}", f"pw{nm}"), (f"pw{nm}", f"to{nm}"),
                  ("hip", f"th{nm}"), (f"th{nm}", f"kn{nm}"), (f"kn{nm}", f"an{nm}"), (f"an{nm}", f"hp{nm}")]
    names = list(nodes)
    sk = bpy.data.meshes.new("_lion_tmp")
    sk.from_pydata([nodes[n][0] for n in names], [(names.index(a), names.index(b)) for a, b in edges], [])
    ob_t = bpy.data.objects.new("_lion_tmp", sk)
    bpy.context.scene.collection.objects.link(ob_t)
    ob_t.modifiers.new("skin", 'SKIN')
    for vi, n in enumerate(names):
        r = nodes[n][1]
        sk.skin_vertices[0].data[vi].radius = (r, r)
    sk.skin_vertices[0].data[names.index("hip")].use_root = True
    sub = ob_t.modifiers.new("sub", 'SUBSURF'); sub.levels = 1
    bpy.context.view_layer.update()
    ev = ob_t.evaluated_get(bpy.context.evaluated_depsgraph_get())
    em = ev.to_mesh()
    vmap = []
    for v in em.vertices:
        f_, s_, u_ = v.co
        vmap.append(bm.verts.new(P(f_ * k, s_ * k, base_z + u_ * k)))
    new_f = []
    for poly in em.polygons:
        try: new_f.append(bm.faces.new([vmap[i] for i in poly.vertices]))
        except ValueError: pass
    paint(new_f, "Marble", MARBLE_D)
    for f in new_f: f.smooth = True   # the one rounded sculpture in a flat-shaded arena
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob_t, do_unlink=True); bpy.data.meshes.remove(sk)
    # the mane: rings of rough lumps framing the face and covering neck and chest (each sunk into the body),
    # two ears on top
    lr = random.Random(5)
    def lump(q, rr, rgb=MARBLE):
        rv = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)["verts"]
        for v in rv:
            v.co = Vector(P((q[0] + v.co.x * rr * 0.8) * k, (q[1] + v.co.y * rr) * k, base_z + (q[2] + v.co.z * rr * 1.2) * k))
        for f in faces_of(rv): f.smooth = True
        paint(faces_of(rv), "Marble", rgb)
    hx, hz = nodes["head"][0][0], nodes["head"][0][2]
    # behind the face only (the snout and brow stay clear), then down the back of the neck
    for ring_x, ring_z, rad, n, rr in ((hx - 0.12, hz, 0.27, 14, 0.14), (hx - 0.24, hz - 0.08, 0.26, 12, 0.17),
                                        (hx - 0.36, hz - 0.18, 0.22, 10, 0.17)):   # a full, heavy mane
        for m_ in range(n):
            a = m_ / n * math.tau + lr.uniform(-0.15, 0.15)
            lump((ring_x + lr.uniform(-0.03, 0.03), math.sin(a) * rad, ring_z + math.cos(a) * rad * 1.1), rr * lr.uniform(0.85, 1.15))
    for m_ in range(9):   # the bib hanging down the front of the chest, under the chin
        lump((0.36 + lr.uniform(-0.03, 0.03), lr.uniform(-0.16, 0.16), 1.02 - m_ * 0.035 - lr.uniform(0, 0.05)), 0.1)
    for sd in (-1, 1):
        lump((hx - 0.02, sd * 0.14, hz + 0.22), 0.06, MARBLE_D)

GAP = 0.42   # half-angle of the opening in the parapet and the stands where the imperial box sits

def ring_gap(r0, r1, z0, z1, seg, mat, rgb):
    """A full ring except the imperial box's sector."""
    return ring(r0, r1, z0, z1, seg, mat, rgb, BOX_A + GAP, BOX_A + math.tau - GAP)

# ---------------------------------------------------------------- the arena floor
# the board's round dais: marble with a gold inlay ring, a step down to the arena floor
ring(0.0, R_DAIS, -0.32, -0.02, 64, "Marble", MARBLE)
ring(R_DAIS - 0.25, R_DAIS - 0.12, -0.02, -0.005, 64, "Gold", GOLD)
ring(R_DAIS, R_DAIS + 0.6, -0.5, -0.2, 64, "Marble", MARBLE_D)
for k in range(16):   # small fire bowls around the dais edge, like the sheet's ring of lamps
    a = (k + 0.5) / 16 * math.tau
    if abs(math.cos(a)) > 0.95 or abs(math.sin(a)) > 0.95: pass
    x, y = math.cos(a) * (R_DAIS + 0.3), math.sin(a) * (R_DAIS + 0.3)
    cyl((x, y, -0.2), 0.08, 0.08, 0.35, 6, "Gold", GOLD)
    cyl((x, y, 0.15), 0.05, 0.16, 0.1, 8, "Gold", GOLD)
    flame((x, y, 0.22), 0.09)
# the floor: radial marble slabs in two tones, a sand border by the wall
n_ring = 5
for i in range(n_ring):
    r0 = R_DAIS + 0.6 + (R_FLOOR - R_DAIS - 0.6) * i / n_ring
    r1 = R_DAIS + 0.6 + (R_FLOOR - R_DAIS - 0.6) * (i + 1) / n_ring
    seg = 24 + i * 4
    for k in range(seg):
        a0, a1 = k / seg * math.tau, (k + 1) / seg * math.tau
        ring(r0 + 0.02, r1 - 0.02, -0.56, -0.5 + rnd.uniform(-0.006, 0.006), 2, "Marble", jit(MARBLE if (i + k) % 2 else MARBLE_D, 0.04), a0 + 0.003, a1 - 0.003)
ring(0.0, 80.0, -0.62, -0.56, 64, "Marble", SAND)   # the grout / far ground under everything, out past the mountains

# ---------------------------------------------------------------- the parapet: wall, pedestals with fire bowls / eagles, banners
ring_gap(R_FLOOR, R_WALL, -0.56, H_WALL, 96, "Marble", MARBLE)
ring_gap(R_FLOOR - 0.06, R_WALL + 0.06, H_WALL, H_WALL + 0.12, 96, "Marble", MARBLE_D)
ring_gap(R_FLOOR - 0.01, R_FLOOR + 0.01, 0.6, 0.72, 96, "Gold", GOLD)   # a gold band along the wall
N_PED = 20
lights = []
for k in range(N_PED):
    a = k / N_PED * math.tau
    if abs((a - BOX_A + math.pi) % math.tau - math.pi) < 0.32: continue   # the stair to the imperial box
    x, y = math.cos(a) * (R_FLOOR - 0.35), math.sin(a) * (R_FLOOR - 0.35)
    top = fire_bowl((x, y, -0.56), 1.0, pedestal=1.6 if k % 2 == 0 else 1.2)
    if k % 2 == 0: lights.append(top)
    else:
        bx, by = math.cos(a + math.pi / N_PED) * R_FLOOR, math.sin(a + math.pi / N_PED) * R_FLOOR
        banner((bx, by, H_WALL - 0.05), 0.7, 1.5, a + math.pi + math.pi / N_PED)
for k in range(N_PED):   # gilded eagles standing on the parapet between the bowls
    a = (k + 0.5) / N_PED * math.tau
    if k % 2: continue
    if abs((a - BOX_A + math.pi) % math.tau - math.pi) < 0.4: continue
    eagle((math.cos(a) * (R_WALL - 0.3), math.sin(a) * (R_WALL - 0.3), H_WALL + 0.12), 0.7, a + math.pi)

# ---------------------------------------------------------------- the stands: stepped tiers packed with a crowd
dz = 0.62
for t in range(N_TIER):
    r0 = R_STAND0 + (R_STAND1 - R_STAND0) * t / N_TIER
    r1 = R_STAND0 + (R_STAND1 - R_STAND0) * (t + 1) / N_TIER
    z = H_WALL + t * dz
    ring_gap(r0, r1, -0.56, z + dz, 96, "Marble", MARBLE if t % 2 else MARBLE_D)
    rm = (r0 + r1) / 2
    n = int(math.tau * rm / 0.58)
    for i in range(n):
        a = (i + rnd.uniform(-0.25, 0.25) + (t % 2) * 0.5) / n * math.tau
        if abs((a - BOX_A + math.pi) % math.tau - math.pi) < GAP + 0.04: continue   # the box and its stair
        if i % 37 == 0: continue                                            # aisles
        if rnd.random() < 0.06: continue
        near_box = abs((a - BOX_A + math.pi) % math.tau - math.pi) < GAP + 0.35 and t < 4
        person((math.cos(a) * rm, math.sin(a) * rm, z + dz), a + math.pi, rnd.uniform(0.8, 0.95),
               legs=t < 3, noble=near_box and rnd.random() < 0.7)
    if t % 3 == 2:   # stairs between sections: darker strips
        pass
TOP = H_WALL + N_TIER * dz

# ---------------------------------------------------------------- the arcade: two storeys of arches with banners and flags
N_ARCH = 48
for s in range(2):
    z0 = TOP + s * 4.0 - (0.6 if s == 0 else 0)
    hgt = 4.0 + (0.6 if s == 0 else 0)
    for k in range(N_ARCH):
        a0, a1 = k / N_ARCH * math.tau, (k + 1) / N_ARCH * math.tau
        am = (a0 + a1) / 2
        # pier
        ring(R_ARCADE, R_ARCADE + 1.0, z0, z0 + hgt, 2, "Marble", MARBLE, a0, a0 + (a1 - a0) * 0.3)
        # opening: dark back wall, then the arch head above it
        ring(R_ARCADE + 0.9, R_ARCADE + 1.0, z0, z0 + hgt * 0.72, 2, "Dark", DARK, a0 + (a1 - a0) * 0.3, a1)
        seg = 6
        for j in range(seg):   # the arch head: a stepped half-round of wall above the opening
            u0, u1 = j / seg, (j + 1) / seg
            h0 = math.sin(math.pi * (u0 + 0.5 / seg)) * 0.22
            ring(R_ARCADE, R_ARCADE + 1.0, z0 + hgt * (0.72 + h0), z0 + hgt, 1, "Marble", MARBLE,
                 a0 + (a1 - a0) * (0.3 + 0.7 * u0), a0 + (a1 - a0) * (0.3 + 0.7 * u1))
        ring(R_ARCADE - 0.05, R_ARCADE + 1.05, z0 + hgt - 0.12, z0 + hgt + 0.12, 2, "Marble", MARBLE_D, a0, a1)   # cornice
        if s == 1 and k % 4 == 0 and abs((am - BOX_A + math.pi) % math.tau - math.pi) > 0.3:
            banner((math.cos(a0 + 0.05) * R_ARCADE, math.sin(a0 + 0.05) * R_ARCADE, z0 + hgt - 0.2), 1.4, 3.2, a0 + 0.05 + math.pi)
ring(R_ARCADE, R_ARCADE + 1.0, TOP + 8.0, TOP + 8.6, 48, "Marble", MARBLE_D)   # attic
for k in range(16):   # flags on poles along the top
    a = (k + 0.5) / 16 * math.tau
    x, y = math.cos(a) * (R_ARCADE + 0.5), math.sin(a) * (R_ARCADE + 0.5)
    cyl((x, y, TOP + 8.6), 0.05, 0.04, 2.6, 6, "Gold", GOLD)
    fa = a + math.pi / 2
    v = [bm.verts.new((x, y, TOP + 11.1)), bm.verts.new((x, y, TOP + 10.3)),
         bm.verts.new((x + math.cos(fa) * 1.1, y + math.sin(fa) * 1.1, TOP + 10.6)), bm.verts.new((x + math.cos(fa) * 1.2, y + math.sin(fa) * 1.2, TOP + 11.15))]
    f = bm.faces.new(v); f.material_index = MI["Cloth"]
    for l in f.loops: l[col] = (*RED, min(1.0, (l.vert.co - Vector((x, y, l.vert.co.z))).length / 1.1))

# ---------------------------------------------------------------- the imperial box: stair, columns, red canopy, throne, two lions
bx, by = math.cos(BOX_A), math.sin(BOX_A)
tx, ty = -by, bx
for i in range(10):   # the stair up from the arena floor
    r = R_FLOOR + 0.1 + i * 0.5
    box((bx * r, by * r, -0.56 + (i + 1) * 0.11), (0.5, 3.2, (i + 1) * 0.22), "Marble", MARBLE if i % 2 else MARBLE_D, BOX_A)   # box(): local x = radial
c0 = Vector((bx, by, 0)) * (R_FLOOR + 6.0)
FLOOR_Z = -0.56 + 10 * 0.22
box((c0.x, c0.y, FLOOR_Z - 0.5), (5.0, 7.0, 1.0), "Marble", MARBLE, BOX_A)   # the box platform
for sd in (-1, 1):
    for dd in (-1.6, 1.6):
        p = c0 + Vector((tx, ty, 0)) * sd * 2.3 + Vector((bx, by, 0)) * dd
        cyl((p.x, p.y, FLOOR_Z), 0.3, 0.26, 4.2, 12, "Marble", MARBLE)
        box((p.x, p.y, FLOOR_Z + 4.3), (0.75, 0.75, 0.2), "Gold", GOLD)
box((c0.x, c0.y, FLOOR_Z + 4.55), (4.2, 5.6, 0.3), "Marble", MARBLE_D, BOX_A)   # entablature (local x = radial)
# pediment with an eagle
for k in range(3):
    box((c0.x - bx * 1.85, c0.y - by * 1.85, FLOOR_Z + 4.85 + k * 0.3), (0.5, 4.6 - k * 1.4, 0.3), "Marble", MARBLE, BOX_A)
eagle((c0.x - bx * 1.85, c0.y - by * 1.85, FLOOR_Z + 5.6), 1.6, BOX_A + math.pi)
# red canopy: a sloped cloth roof and hanging drapes
for sd in (-1, 1):
    banner((c0.x + tx * sd * 2.2 - bx * 2.1, c0.y + ty * sd * 2.2 - by * 2.1, FLOOR_Z + 4.4), 1.1, 3.0, BOX_A + math.pi, emblem=False, gap=0.04)
banner((c0.x - bx * 2.1, c0.y - by * 2.1, FLOOR_Z + 4.4), 2.2, 2.4, BOX_A + math.pi, gap=0.04)
# the throne
box((c0.x + bx * 1.2, c0.y + by * 1.2, FLOOR_Z + 0.5), (1.0, 1.0, 1.0), "Gold", GOLD, BOX_A)
box((c0.x + bx * 1.65, c0.y + by * 1.65, FLOOR_Z + 1.4), (0.2, 1.1, 1.8), "Cloth", RED, BOX_A)
# the back of the box: a wall closing the gap in the stands up to the arcade, hung with a great banner
ring(R_ARCADE - 0.7, R_ARCADE, -0.56, TOP, 8, "Marble", MARBLE_D, BOX_A - GAP - 0.02, BOX_A + GAP + 0.02)
banner((bx * (R_ARCADE - 0.7), by * (R_ARCADE - 0.7), TOP - 0.3), 3.0, 4.6, BOX_A + math.pi)
for sd in (-1, 1):   # side walls of the box, carrying the cut-off tiers
    p = Vector((bx, by, 0)) * ((R_STAND0 + R_ARCADE) / 2)
    a = BOX_A + sd * (GAP + 0.01)
    q = Vector((math.cos(a), math.sin(a), 0)) * ((R_STAND0 + R_ARCADE) / 2)
    box((q.x, q.y, (TOP - 0.56) / 2), (R_ARCADE - R_STAND0, 0.4, TOP + 0.56), "Marble", MARBLE, a)
# the lions flanking the stair, on the parapet line
for sd in (-1, 1):
    p = Vector((bx, by, 0)) * (R_FLOOR + 0.6) + Vector((tx, ty, 0)) * sd * 2.4
    lion((p.x, p.y, -0.56), 1.3, BOX_A + math.pi)   # plinth on the floor (slabs top -0.5)

# ---------------------------------------------------------------- mountains far off (a jagged ring, fogged)
N_M = 64
base = [bm.verts.new((math.cos(i / N_M * math.tau) * 70, math.sin(i / N_M * math.tau) * 70, -0.7)) for i in range(N_M)]   # rooted in the ground
peak = [bm.verts.new((math.cos(i / N_M * math.tau) * 72, math.sin(i / N_M * math.tau) * 72,
                      6 + 10 * abs(math.sin(i * 0.9)) * rnd.uniform(0.5, 1.2) + (8 if i % 7 == 3 else 0))) for i in range(N_M)]
mf = [bm.faces.new((base[i], base[(i + 1) % N_M], peak[(i + 1) % N_M], peak[i])) for i in range(N_M)]
paint(mf, "Dark", (0.42, 0.33, 0.33))

# ---------------------------------------------------------------- into its own scene and out to the engines
bpy.app.driver_namespace["arena_lights"] = lights
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in mf: f.normal_flip()   # the mountain ring is seen from inside
bmesh.ops.triangulate(bm, faces=bm.faces[:])
sc = bpy.data.scenes.get("Arena") or bpy.data.scenes.new("Arena")
for o in list(sc.collection.objects): bpy.data.objects.remove(o, do_unlink=True)
me = bpy.data.meshes.get("Arena") or bpy.data.meshes.new("Arena")
me.materials.clear()   # the slots exist before to_mesh, or every material index is clamped to 0
for n in MATS:
    m = bpy.data.materials.get("Arena" + n) or bpy.data.materials.new("Arena" + n)
    m.use_nodes = True
    nt = m.node_tree   # base colour from the vertex colours: the glTF exporter only writes colours a material uses
    bsdf = next(nd for nd in nt.nodes if nd.type == "BSDF_PRINCIPLED")
    vc = next((nd for nd in nt.nodes if nd.type == "VERTEX_COLOR"), None) or nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    me.materials.append(m)
bm.to_mesh(me); bm.free()   # faces keep their own smooth flag (flat everywhere but the lions)
# the motion weight again as its own per-vertex attribute "_w": the glTF exporter drops colour alpha
# (the web viewer reads _w, Unity's FBX keeps the alpha)
wv = [0.0] * len(me.vertices)
cd = me.color_attributes["Col"].data
for li, lp in enumerate(me.loops): wv[lp.vertex_index] = max(wv[lp.vertex_index], cd[li].color[3])
wa = me.attributes.get("_w") or me.attributes.new("_w", 'FLOAT', 'POINT')
wa.data.foreach_set("value", wv)
# and the colour as "_c" (linear rgb): the glTF exporter wrote COLOR_0 only for the first material's primitive
cv = [0.0] * (3 * len(me.vertices))
for li, lp in enumerate(me.loops): cv[3 * lp.vertex_index:3 * lp.vertex_index + 3] = cd[li].color[:3]
ca = me.attributes.get("_c") or me.attributes.new("_c", 'FLOAT_VECTOR', 'POINT')
ca.data.foreach_set("vector", cv)
me.color_attributes.active_color = me.color_attributes["Col"]   # the glTF exporter writes the ACTIVE colour layer only
me.color_attributes.render_color_index = me.color_attributes.active_color_index
ob = bpy.data.objects.new("Arena", me)
sc.collection.objects.link(ob)
bpy.app.driver_namespace["arena_tris"] = len(me.polygons)

win = bpy.context.window; prev = win.scene
for o in prev.objects: o.select_set(False)   # the pieces' scene: nothing of it may ride along
win.scene = sc
for o in sc.objects: o.select_set(False)
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=OUT_FBX, use_selection=True, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                         axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', object_types={'MESH'}, colors_type='LINEAR')
scrub_user(OUT_FBX)
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True, use_active_scene=True, export_yup=True,
                          export_animations=False, export_vertex_color='MATERIAL', export_attributes=True)
win.scene = prev
