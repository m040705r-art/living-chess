# Keyframed battle clips for the warrior pieces (24 fps). Run after warriors.py has built the rigs.
# Rotation conventions (bone rolls set by warriors.make_rig, verified by probing):
#   +X  = swing forward / flex (arms, thighs, spine lean forward). Knees bend with -X on the shin.
#   Z   = sideways: left arm +Z raises it, right arm -Z raises it.
#   spine/chest +Z leans to the piece's right, hips/spine Y twists.
#   root carries the pedestal: location in board units (-Y = forward), rotation X tips the whole statue.
# Prop bones (weapon / shield) are AIMED per key in armature space, so a spear stays upright whatever the arm does.
import bpy, math
from mathutils import Vector, Matrix, Euler

FPS = 24
LOC_REF = 0.34   # piece scale the root offsets (lunges, falls) were authored at

def P(*parts, **bones):
    d = {}
    for p in parts:
        for k, v in p.items():
            d[k] = {**d.get(k, {}), **v} if k.startswith("_") else v   # "_arms" merges per bone
    for k, v in bones.items(): d[k.replace("_L", ".L").replace("_R", ".R")] = v
    return d

def add(a, b):
    out = dict(a)
    for k, v in b.items():
        if k.startswith("_"): out[k] = {**out.get(k, {}), **v}; continue   # "_arms" etc. merge, not sum
        out[k] = tuple(x + y for x, y in zip(out.get(k, (0, 0, 0)), v))
    return out

def ARMS(**dirs):
    """Point arm bones along directions given in the CHEST's frame (x = piece's left, -y = forward, z = up),
    e.g. ARMS(upper_arm_R=(-0.3, -0.2, -0.9), forearm_R=(0, -1, 0.1)) -> a clear 90 degree elbow.
    Directions follow the torso, so leaning/twisting the spine carries the arms with it."""
    return {"_arms": {k.replace("_L", ".L").replace("_R", ".R"): v for k, v in dirs.items()}}

ARM_ORDER = ("upper_arm.L", "forearm.L", "hand.L", "upper_arm.R", "forearm.R", "hand.R")

def point_arms(rig, arms):
    pbs = rig.pose.bones
    ch = pbs["chest"]
    C = ch.matrix.to_3x3() @ ch.bone.matrix_local.to_3x3().inverted()
    for bn in ARM_ORDER:
        if bn not in arms: continue
        pb = pbs[bn]
        cur = pb.matrix
        R = cur.col[1].xyz.normalized().rotation_difference((C @ Vector(arms[bn])).normalized()).to_matrix()
        pb.matrix = Matrix.Translation(cur.translation) @ (R @ cur.to_3x3()).to_4x4()
        bpy.context.view_layer.update()

def aim_bone(rig, bone, y_dir, z_hint):
    """Rotate a prop bone so its local Y points along y_dir (armature space) and Z leans toward z_hint."""
    pb = rig.pose.bones[bone]
    y = Vector(y_dir).normalized()
    z = Vector(z_hint); z = (z - y * y.dot(z)).normalized()
    pb.matrix = Matrix.Translation(pb.matrix.translation) @ Matrix((y.cross(z), y, z)).transposed().to_4x4()
    bpy.context.view_layer.update()

def apply_aim(rig, bone, yd, zh, R):
    """yd == "strap": the prop is strapped to its parent forearm -> face points along zh but is kept
    perpendicular to the forearm, so the arm always lies flat behind it (no fist poking through)."""
    if yd == "strap":
        fa = rig.pose.bones[bone].parent
        f = fa.matrix.col[1].xyz.normalized()
        n = R @ Vector(zh); n = (n - f * f.dot(n)).normalized()
        up = R @ Vector((0, 0, 1)); y = up - n * n.dot(up)
        aim_bone(rig, bone, y, n)
    else:
        y, z = resolve_aim(rig, bone, yd, zh, R)
        aim_bone(rig, bone, y, z)

def resolve_aim(rig, bone, yd, zh, R):
    """Plain (y_dir, z_hint) aims are relative to the (possibly tipped) statue;
    yd == "target": point the prop at armature-space point zh (e.g. the opponent's chest)."""
    if yd == "target":
        return Vector(zh) - rig.pose.bones[bone].head, Vector((0, 0, 1))
    return R @ Vector(yd), R @ Vector(zh)

GROUND_CFG = {}   # rig name -> (ground points, bone to shift); pieces without an entry use the humanoid hips
GROUND_PTS = (("foot", "head", 0.09), ("foot", "tail", 0.03), ("shin", "head", 0.075))   # ankle, toe, knee: clearance (m)

def ground(rig, sc):
    """Slide the hips up/down so the lowest foot (or knee, when kneeling) just touches the board.
    Hand-tuned hip drops left the boots sunk into the floor once the pedestal was gone."""
    pbs = rig.pose.bones
    pts, bone = GROUND_CFG.get(rig.name, (GROUND_PTS, "hips"))
    low = min(getattr(pbs[f"{b}.{s}"], end).z - c * sc for b, end, c in pts for s in "LR")
    low -= pbs["root"].head.z
    if abs(low) > 1e-5:   # shift in armature space, whatever way the bone points
        pb = pbs[bone]
        pb.matrix = Matrix.Translation((0, 0, -low)) @ pb.matrix
        bpy.context.view_layer.update()

def bake_ground(rig, keys, sc):
    """Keep feet on the board on every frame while the statue is upright (interpolated hips sank between keys).
    Frames where the whole piece is tipping (falls) are left to the keyed motion."""
    scene = bpy.context.scene
    hips = rig.pose.bones[GROUND_CFG.get(rig.name, (None, "hips"))[1]]
    for f in range(keys[0]["f"], keys[-1]["f"] + 1):
        scene.frame_set(f)
        r = rig.pose.bones["root"].rotation_euler
        if max(abs(r.x), abs(r.y)) > math.radians(12): continue
        ground(rig, sc)
        hips.keyframe_insert("location", frame=f)

def K(f, pose, loc=None, rot=None, drop=0.0, aims=None):
    """One key: root loc (board units), root rot (deg), hips drop (human metres, + = down), extra aims."""
    return dict(f=f, pose=pose, loc=loc, rot=rot, drop=drop, aims=aims)

def bake_aims(rig, keys, aims):
    """Re-aim prop bones on every in-between frame, blending the two neighbouring keys' directions.
    Euler interpolation in hand space would otherwise whip a long spear through big arcs."""
    def table(k):
        t = {a[0]: a for a in aims}
        for a in (k["aims"] or ()): t[a[0]] = a
        return {b: a for b, a in t.items() if a[1] is not None and b not in k["pose"]}
    sc = bpy.context.scene
    for k0, k1 in zip(keys, keys[1:]):
        t0, t1 = table(k0), table(k1)
        for f in range(k0["f"] + 1, k1["f"]):
            u = (f - k0["f"]) / (k1["f"] - k0["f"])
            u = u * u * (3 - 2 * u)   # match the ease of Bezier keys
            sc.frame_set(f)
            rr = rig.pose.bones["root"].rotation_euler
            R = Euler((rr.x, rr.y, rr.z)).to_matrix()
            for bone in set(t0) & set(t1):
                a, b = t0[bone], t1[bone]
                if "strap" in (a[1], b[1]):
                    apply_aim(rig, bone, "strap", Vector(a[2]).lerp(Vector(b[2]), u), R)
                    rig.pose.bones[bone].keyframe_insert("rotation_euler", frame=f)
                    continue
                ya, za = resolve_aim(rig, bone, a[1], a[2], R)
                yb, zb = resolve_aim(rig, bone, b[1], b[2], R)
                y = ya.normalized().lerp(yb.normalized(), u)
                z = za.normalized().lerp(zb.normalized(), u)
                if y.length < 1e-3: continue
                aim_bone(rig, bone, y, z)
                rig.pose.bones[bone].keyframe_insert("rotation_euler", frame=f)

def natural_wrist(rig, act, hand, prop="weapon", pinned=lambda f: False, tip=None, edge=False):
    """Bend the wrist so the fist closes around the grip: the hand's length axis is turned square to the
    blade (forearm direction with the blade component removed). Prop aims used to swing the weapon while the
    hand stayed rigid on the forearm, so the fist pointed one way and the grip another (user: wrists look odd).
    The prop keeps its world orientation (recorded first, then restored) and simply rides along with the fist."""
    sc = bpy.context.scene
    pbs = rig.pose.bones
    rig.animation_data.action = act
    f0, f1 = (int(x) for x in act.frame_range)
    own = rig.pose.bones[prop].parent.name == hand
    rec = {}
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        rec[f] = pbs[prop].matrix.copy()
    prev = None
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        b = rec[f].col[1].xyz.normalized()
        fa = pbs[pbs[hand].parent.name].matrix.col[1].xyz.normalized()
        y = fa - b * fa.dot(b)
        # square to the blade, so the grip runs straight through the closed fist (warriors.fist builds the fingers
        # round the hand's -X). When the blade lies along the forearm (a couched lance) "square" is undefined and
        # the hand used to snap ~90 degrees between frames (user: "槍がブレブレ"): there, keep last frame's hand
        # direction and only ease toward the forearm-derived one as it becomes well defined.
        w = min(1.0, max(0.0, (y.length - 0.05) / 0.3))
        y = y.normalized() if y.length > 1e-6 else (prev or fa)
        if prev is not None:   # turn about the blade from last frame's hand direction, at most 14 deg a frame
            p_ = prev - b * prev.dot(b)
            if p_.length > 1e-6:
                p_.normalize()
                ang = math.atan2(p_.cross(y).dot(b), p_.dot(y))
                step = max(-math.radians(14), min(math.radians(14), ang * w))
                y = (Matrix.Rotation(step, 3, b) @ p_).normalized()
        prev = y.copy()
        aim_bone(rig, hand, y, y.cross(b))
        pbs[hand].keyframe_insert("rotation_euler", frame=f)
        if own:
            pb = pbs[prop]
            pin = pinned(f)
            if pin: pb.matrix = rec[f]
            elif tip:   # keep the POINT where it was (contacts were solved for it), re-aim from the moved grip
                old = rec[f].translation + rec[f].col[1].xyz.normalized() * tip
                aim_bone(rig, prop, old - pb.matrix.translation, rec[f].col[2].xyz)
            else: pb.matrix = Matrix.Translation(pb.matrix.translation) @ rec[f].to_3x3().to_4x4()
            bpy.context.view_layer.update()
            if edge and not pin:   # roll the blade about its own axis so its edges line up with the fist (knuckles
                # to wrist) - a pure roll, so the point does not move (user: "剣のガードとブレードの向きがおかしすぎる")
                rest = pb.bone.matrix_local.to_3x3()
                d0 = rest.col[1].normalized()
                w_local = rest.transposed() @ (Vector((0, 0, 1)).rotation_difference(d0).to_matrix() @ Vector((0, 1, 0)))
                M = pb.matrix.to_3x3(); bb = M.col[1].normalized()
                W = M @ w_local; W = (W - bb * W.dot(bb)).normalized()
                hy = pbs[hand].matrix.col[1].xyz; T = hy - bb * hy.dot(bb)
                if T.length > 1e-4:
                    T.normalize()
                    if W.dot(T) < 0: T = -T   # an edge is an edge: take the nearer of the two
                    ang = math.atan2(W.cross(T).dot(bb), W.dot(T))
                    pb.matrix = Matrix.Translation(pb.matrix.translation) @ (Matrix.Rotation(ang, 3, bb) @ M).to_4x4()
                    bpy.context.view_layer.update()
            pb.keyframe_insert("rotation_euler", frame=f)
            pb.keyframe_insert("location", frame=f)
    rig.animation_data.action = None

def ramp(pts, f):
    """Piecewise-linear weight from [(frame, w), ...]."""
    if f <= pts[0][0]: return pts[0][1]
    for (f0, w0), (f1, w1) in zip(pts, pts[1:]):
        if f <= f1: return w0 + (w1 - w0) * (f - f0) / max(1e-6, f1 - f0)
    return pts[-1][1]

def remove_fcurves(act, test):
    for ly in getattr(act, "layers", ()):
        for st in ly.strips:
            for cb in st.channelbags:
                for fc in [fc for fc in cb.fcurves if test(fc)]: cb.fcurves.remove(fc)

def hilt_ik(rig, act, pts):
    """Rest both wrists on the dagger hilts (bones hilt.L / hilt.R) with weights pts, baked into the arm keys."""
    pbs = rig.pose.bones
    cons = []
    sides = [sd for sd in "LR" if f"hilt.{sd}" in pbs]   # the knight has one sword (hilt.R only)
    for side in sides:
        ik = pbs[f"forearm.{side}"].constraints.new('IK'); ik.target = rig; ik.subtarget = f"hilt.{side}"; ik.chain_count = 2
        cons.append(ik)
    rig.animation_data.action = act
    f0, f1 = (int(x) for x in act.frame_range)
    for f in range(f0, f1 + 1):
        for side, ik in zip(sides, cons):
            ik.influence = ramp(pts[side] if isinstance(pts, dict) else pts, f); ik.keyframe_insert("influence", frame=f)
    for o in bpy.context.selected_objects: o.select_set(False)   # bake acts on the ACTIVE armature: with several
    rig.select_set(True); bpy.context.view_layer.objects.active = rig   # pieces built it was another one ("Nothing to bake")
    bpy.ops.object.mode_set(mode='POSE')
    for b in pbs: b.select = b.name in ("upper_arm.L", "forearm.L", "upper_arm.R", "forearm.R")
    bpy.ops.nla.bake(frame_start=f0, frame_end=f1, only_selected=True, visual_keying=True, clear_constraints=True,
                     use_current_action=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    remove_fcurves(act, lambda fc: "influence" in fc.data_path or fc.data_path.endswith(".scale"))
    for b in pbs: b.scale = (1, 1, 1)
    for side in "LR":   # nla.bake's clear_constraints left them on: every later clip (and the export) kept the
        fa = pbs[f"forearm.{side}"]   # fists glued to the belt (user: "抜刀後に短剣と腰がくっついてる")
        for c in [c for c in fa.constraints if c.type == 'IK']: fa.constraints.remove(c)
    rig.animation_data.action = None

def sheath_pass(rig, act, pts):
    """Blend each dagger between the fist (w=0) and its scabbard on the belt (w=1, bone sheath.X), keyed every frame."""
    sc = bpy.context.scene
    pbs = rig.pose.bones
    rig.animation_data.action = act
    f0, f1 = (int(x) for x in act.frame_range)
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        for prop, side in (("weapon", "R"), ("weapon.L", "L")):
            if prop not in pbs or f"sheath.{side}" not in pbs: continue
            w = ramp(pts[side] if isinstance(pts, dict) else pts, f)
            pb, M = pbs[prop], pbs[f"sheath.{side}"].matrix
            y = M.col[1].xyz.normalized(); z = M.col[0].xyz; z = (z - y * y.dot(z)).normalized()
            S = Matrix.Translation(M.translation) @ Matrix((y.cross(z), y, z)).transposed().to_4x4()
            H = pb.matrix.copy()
            loc = H.translation.lerp(S.translation, w)
            rot = H.to_quaternion().slerp(S.to_quaternion(), w)
            pb.matrix = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
            bpy.context.view_layer.update()
            pb.keyframe_insert("rotation_euler", frame=f); pb.keyframe_insert("location", frame=f)
    rig.animation_data.action = None

def fcurves(act):
    """F-curves of an action (Blender 4.4+ slotted actions keep them in layers/strips/channelbags)."""
    if hasattr(act, "layers"):
        return [fc for ly in act.layers for st in ly.strips for cb in st.channelbags for fc in cb.fcurves]
    return list(act.fcurves)

def clip(rig, name, keys, loop=False, aims=(), flowing=False):
    """aims: (bone, y_dir, z_hint) applied to every key unless the key's pose sets that bone or the key
    overrides it via K(aims=[...]); an override entry (bone, None, None) lets the prop follow the hand."""
    sc = rig.get("piece_scale", 1.0)
    act = bpy.data.actions.new(f"{rig.name}|{name}")
    act.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = act
    pbs = rig.pose.bones
    for k in keys:
        pose = k["pose"]
        for b in pbs:
            b.rotation_mode = 'XYZ'
            b.scale = (1, 1, 1)   # a stray pose scale (left by a bake) skewed every later matrix: arms stretched to 3x
            if b.name == "root":   # root offsets were authored for a 0.34-scale piece; grow with the piece
                b.location = Vector(k["loc"] or (0, 0, 0)) * (sc / LOC_REF)
                b.rotation_euler = [math.radians(v) for v in (k["rot"] or (0, 0, 0))]
            else:
                b.rotation_euler = [math.radians(v) for v in pose.get(b.name, (0, 0, 0))]
                b.location = (0, -k["drop"] * sc, 0) if b.name == "hips" else (0, 0, 0)   # hips local +Y = up
        bpy.context.view_layer.update()
        point_arms(rig, pose.get("_arms", {}))
        if k["rot"] is None or max(abs(k["rot"][0]), abs(k["rot"][1])) < 12:
            ground(rig, sc)
        R = Euler([math.radians(v) for v in (k["rot"] or (0, 0, 0))]).to_matrix()   # aims tip with the statue
        table = {a[0]: a for a in aims}
        for a in (k["aims"] or ()): table[a[0]] = a
        for bone, yd, zh in table.values():
            if yd is not None and bone not in pose:
                apply_aim(rig, bone, yd, zh, R)
        for b in pbs:   # location too, on every bone: a channel a clip leaves unkeyed keeps whatever another clip
            b.keyframe_insert("rotation_euler", frame=k["f"])   # left there (a sheathed dagger's offset stuck in the fist)
            b.keyframe_insert("location", frame=k["f"])
    bake_aims(rig, keys, aims)
    bake_ground(rig, keys, sc)
    if flowing:   # free (non-clamped) Bezier handles: keeps momentum through keys instead of easing into each
        for fc in fcurves(act):
            for kp in fc.keyframe_points: kp.handle_left_type = kp.handle_right_type = 'AUTO'
            fc.update()
    act.frame_range = (keys[0]["f"], keys[-1]["f"])
    act.use_frame_range = True
    act.use_cyclic = loop
    rig.animation_data.action = None
    return act

# ---------------------------------------------------------------- Pawn: a dagger fighter (one long dagger in each fist)
# Arms are posed by direction (ARMS, chest frame: x = piece's left, -y = forward, z = up) so elbows bend clearly.
# Pawn vs pawn is fought at close quarters: the daggers are short, so the two pawns square up PAWN_DUEL squares
# apart (the game / viewer walks the attacker in to that distance). Other pieces still strike a pawn one square
# ahead of them (T_CHEST).
PAWN_DUEL = 1.0   # with the longer daggers (user: 短剣短すぎる) the pawns fight a full square apart again
STAND = P({"thigh.L": (22, 0, 7), "shin.L": (-38, 0, 0), "foot.L": (12, 0, 0)},     # compact: knees bent, feet under the body
          {"thigh.R": (0, 0, -7), "shin.R": (-30, 0, 0), "foot.R": (20, 0, 0)})
GUARD_ARMS = ARMS(upper_arm_R=(-0.3, -0.3, -0.9), forearm_R=(-0.1, -0.95, 0.2),     # elbows in, both blades
                  upper_arm_L=(0.3, -0.3, -0.9), forearm_L=(0.1, -0.95, 0.2))       # held up before the body
T_CHEST = (0.0, -1.06, 0.68)     # opponent pawn's chest, in the attacker's space (opponent one square ahead)
T_P_CHEST = (0.0, -PAWN_DUEL - 0.08, 0.68)   # the same, at duelling distance (a hand's width into the body)
T_GUARD = (-0.063, -0.71, 0.755)    # where the defender's crossed daggers meet at frame 16 of Block/Hit (solved)
T_SHIELD = (T_GUARD[0], T_GUARD[1] - (1 - PAWN_DUEL), T_GUARD[2])   # the guard seen from one square (knight_anims)
# Second storyboard ("通常コンボ / 重攻撃 / ラッシュ / 反撃・カウンター / ダメージ"): every hit before the kill lands on
# the defender's crossed blades (T_GUARD), never the body. (frame, blade, wind-up style); styles: side / up / down / spin
PAWN_COMBOS = {
    "Combo": [(9, "weapon", "side"), (14, "weapon.L", "side"), (19, "weapon", "up"), (24, "weapon.L", "down"),
              (32, "weapon", "side"), (37, "weapon.L", "side")],
    "Heavy": [(17, "weapon", "down"), (23, "weapon.L", "side"), (29, "weapon", "side")],
    "Rush": [(8, "weapon", "side"), (11, "weapon.L", "side"), (14, "weapon", "up"), (17, "weapon.L", "down"),
             (20, "weapon", "side"), (26, "weapon.L", "side"), (29, "weapon", "side"), (32, "weapon.L", "side")],
    "Counter": [(26, "weapon", "side"), (31, "weapon.L", "side"), (36, "weapon", "up")],
}
# (clip, frame) -> root lunge (authoring units), solved in Blender so the cut (SLASH_CUT point) lands on the guard
# the knight's sword strings (knight_anims.py) that a pawn has to take on its crossed blades
KNIGHT_COMBO_FRAMES = (8, 13, 18, 23, 28, 33, 38, 45)
KNIGHT_SKILL_GUARD, KNIGHT_SKILL_KILL = (22, 28), 36
QUEEN_COMBO_FRAMES = (8, 13, 18, 23, 28, 34, 40, 46, 52, 58)
KNIGHT_MACE_GUARD, KNIGHT_MACE_KILL = (20, 26, 32), 40   # knight_anims.py Attack (morning star, 16 beats)   # queen_anims.py Combo: the staff blows
PAWN_LUNGE = {('Combo', 9): -0.1262, ('Combo', 14): -0.2591, ('Combo', 19): -0.1273, ('Combo', 24): -0.259, ('Combo', 32): -0.1262, ('Combo', 37): -0.2591, ('Heavy', 17): -0.1262, ('Heavy', 23): -0.2591, ('Heavy', 29): -0.1262, ('Rush', 8): -0.1262, ('Rush', 11): -0.2591, ('Rush', 14): -0.1262, ('Rush', 17): -0.2591, ('Rush', 20): -0.1262, ('Rush', 26): -0.2591, ('Rush', 29): -0.1262, ('Rush', 32): -0.2591, ('Counter', 26): -0.1262, ('Counter', 31): -0.259, ('Counter', 36): -0.127}
PAWN_EVENTS = {}  # clip -> [[frame, bone]]: written to WebPreview/models/Pawn_events.json by export.py
DODGE = 0.4   # sideways sway of Dodge (authoring units): checked in Blender, the spin slash misses by >= 10 cm
SLASH_CUT = 0.85   # a slash cuts with the outer blade: the point 85% out from the guard is solved onto T_SLASH
T_SLASH = (0.0, -PAWN_DUEL + 0.05, 0.68)   # inside the chest, short of its centre (no body-to-body overlap)
T_CLASH = (0.0, -PAWN_DUEL / 2 - 0.02, 0.74)   # both pawns' points meet just past the midpoint
LUNGE_KILL, LUNGE_BLOCKED, LUNGE_CLASH = -0.2642, -0.1263, -0.0029   # root lunge (authoring units), solved in Blender (kill re-solved for the straight-elbow attack)
GUARD = P(STAND, GUARD_ARMS, spine=(16, 0, 0), chest=(4, 0, 0), head=(-16, 0, 0), hips=(0, 8, 0))
GD = 0.1
DAG_R = ("weapon", (-0.15, -0.85, 0.5), (0, 0, 1))   # points forward and up, close to the centre line
DAG_L = ("weapon.L", (0.15, -0.85, 0.5), (0, 0, 1))

def mirror(pose):
    """Left/right mirror of a pose dict (swap .L/.R, flip sideways components)."""
    sw = lambda n: n[:-2] + (".R" if n.endswith(".L") else ".L") if n[-2:] in (".L", ".R") else n
    out = {}
    for k, v in pose.items():
        if k == "_arms":
            out[k] = {sw(b): (-d[0], d[1], d[2]) for b, d in v.items()}
        else:
            out[sw(k)] = (v[0], -v[1], -v[2])
    return out
FREE = [("weapon", None, None), ("weapon.L", None, None)]

def pawn_clips(rig):
    g = GUARD
    hold = (DAG_R, DAG_L)
    out = []
    # Sheathed: standing easy, both hands resting on the dagger hilts at the belt (wrists IK'd onto hilt.L/R)
    rest = P({"thigh.L": (6, 0, 3), "shin.L": (-8, 0, 0), "foot.L": (2, 0, 0), "thigh.R": (-2, 0, -3), "shin.R": (-6, 0, 0), "foot.R": (8, 0, 0)},
             ARMS(upper_arm_R=(-0.25, -0.3, -0.92), forearm_R=(0.8, -0.45, -0.4),    # arms crossed over the belt,
                  upper_arm_L=(0.25, -0.4, -0.88), forearm_L=(-0.8, -0.5, -0.33)),   # each hand on the opposite hilt
             spine=(3, 0, 0), head=(-2, 0, 0))
    out.append(clip(rig, "Idle", [
        K(1, rest), K(24, add(rest, P(chest=(-2, 0, 0), head=(0, 10, 0)))), K(48, add(rest, P(head=(0, -9, 0), spine=(0, 0, 2)))),
        K(72, rest)], loop=True, aims=FREE))
    def wstep(s):
        return P(rest, {"thigh.L": (20 * s, 0, 3), "shin.L": (-20 if s > 0 else -26, 0, 0), "foot.L": (12 if s > 0 else -8, 0, 0)},
                 {"thigh.R": (-20 * s, 0, -3), "shin.R": (-26 if s > 0 else -20, 0, 0), "foot.R": (-8 if s > 0 else 12, 0, 0)},
                 spine=(6, 0, 0), chest=(2, -5 * s, 0), hips=(0, 6 * s, 0))
    def wplant(lift):
        o = "R" if lift == "L" else "L"; side = 1 if lift == "L" else -1
        return P(rest, {f"thigh.{lift}": (24, 0, 0), f"shin.{lift}": (-48, 0, 0), f"foot.{lift}": (16, 0, 0),
                        f"thigh.{o}": (2, 0, 0), f"shin.{o}": (-8, 0, 0), f"foot.{o}": (6, 0, 0)},
                 spine=(7, 0, 7 * side), chest=(2, 0, 3 * side), hips=(0, 0, -4 * side), head=(-2, 0, -5 * side))
    out.append(clip(rig, "Walk", [
        K(1, wstep(1)), K(13, wplant("R")), K(25, wstep(-1)), K(37, wplant("L")), K(49, wstep(1))], loop=True, aims=FREE))
    # Draw: grips the hilts, rips both daggers up out of the scabbards and drops into the fighting guard
    grip = add(rest, P(spine=(8, 0, 0), head=(-4, 0, 0), thigh_L=(10, 0, 0), shin_L=(-14, 0, 0), shin_R=(-10, 0, 0)))
    # cross draw: both blades whip out of the opposite scabbards and sweep wide and up
    rip = P(STAND, ARMS(upper_arm_R=(-0.7, -0.1, -0.7), forearm_R=(-0.55, -0.45, 0.7),
                        upper_arm_L=(0.7, -0.1, -0.7), forearm_L=(0.55, -0.45, 0.7)),
            spine=(-4, 0, 0), chest=(-4, 0, 0), head=(-8, 0, 0))
    out_ = [("weapon", (-0.6, -0.3, 0.75), (0, -1, 0)), ("weapon.L", (0.6, -0.3, 0.75), (0, -1, 0))]
    # Ready: crouched and wary, weight shifting, daggers turning (daggers drawn)
    # never still: a fighter's bounce, the weight rocking from foot to foot, the blades turning (user: "ぎこちない")
    rock = lambda sd: add(g, P(hips=(0, 5 * sd, 0), spine=(2, -4 * sd, -3 * sd), head=(0, 6 * sd, 0),
                               thigh_L=(4 * sd, 0, 0), thigh_R=(-4 * sd, 0, 0)))
    turn = lambda sd: [("weapon", (-0.45 + 0.1 * sd, -0.85, -0.2 + 0.12 * sd), (0, 0, 1)),
                       ("weapon.L", (0.45 + 0.1 * sd, -0.85, -0.2 - 0.12 * sd), (0, 0, 1))]
    out.append(clip(rig, "Ready", [
        K(1, g, drop=GD), K(7, rock(1), drop=GD + 0.035, aims=turn(1)), K(13, g, drop=GD),
        K(19, rock(-1), drop=GD + 0.035, aims=turn(-1)), K(25, g, drop=GD)], loop=True, aims=hold, flowing=True))
    # Attack: the design sheet's spinning double slash. Wound up to the right, the pawn spins a full turn on the
    # spot (root Z) with both blades held wide; the right blade cuts through the chest on frame 16 as the spin
    # completes and the left one follows round. AttackBlocked: a heavy straight thrust stopped on the guard.
    coil = P({"thigh.L": (30, 0, 14), "shin.L": (-50, 0, 0), "foot.L": (16, 0, 0),
              "thigh.R": (-4, 0, -14), "shin.R": (-40, 0, 0), "foot.R": (30, 0, 0)},
             ARMS(upper_arm_R=(-0.35, 0.5, -0.8), forearm_R=(0.0, -0.9, 0.4),
                  upper_arm_L=(0.3, -0.45, -0.84), forearm_L=(0.05, -0.85, 0.5)),
             spine=(18, 16, 0), chest=(4, 8, 0), hips=(0, 14, 0), head=(-18, -10, 0))   # right shoulder drawn back
    stab = P({"thigh.L": (44, 0, 10), "shin.L": (-46, 0, 0), "foot.L": (0, 0, 0),
              "thigh.R": (-26, 0, -10), "shin.R": (-14, 0, 0), "foot.R": (36, 0, 0)},
             ARMS(upper_arm_R=(0.22, -0.97, -0.05), forearm_R=(0.38, -0.92, 0.08),   # aimed across: the chest is turned
                  upper_arm_L=(0.6, -0.1, -0.8), forearm_L=(0.5, -0.6, 0.4)),
             spine=(24, -18, 0), chest=(8, -10, 0), hips=(0, -16, 0), head=(-22, 8, 0))   # right shoulder leads
    wind = P(STAND, ARMS(upper_arm_R=(0.1, -0.5, -0.85), forearm_R=(0.6, -0.6, 0.5),       # right blade cocked at the left shoulder
                         upper_arm_L=(0.35, -0.3, -0.88), forearm_L=(0.15, -0.95, 0.2)),
             spine=(14, 18, 0), chest=(4, 8, 0), hips=(0, 6, 0), head=(-14, -12, 0))
    # the attack swings with the elbows straight (user: "ポーンの攻撃肘を伸ばして"); only the wind-up bends them
    whirl = P(STAND, ARMS(upper_arm_R=(-0.55, -0.7, -0.45), forearm_R=(-0.55, -0.76, -0.35),   # both arms reaching out front
                          upper_arm_L=(0.55, -0.7, -0.45), forearm_L=(0.55, -0.76, -0.35)),
              spine=(12, 0, 0), head=(-12, 0, 0))
    slash = P({"thigh.L": (40, 0, 12), "shin.L": (-50, 0, 0), "foot.L": (6, 0, 0),
               "thigh.R": (-20, 0, -12), "shin.R": (-20, 0, 0), "foot.R": (34, 0, 0)},
              ARMS(upper_arm_R=(0.08, -0.99, -0.05), forearm_R=(0.12, -0.99, -0.02),   # arm at full stretch, elbow locked
                   upper_arm_L=(0.85, 0.2, -0.45), forearm_L=(0.88, 0.25, -0.38)),      # the left flung straight out behind
              spine=(26, -14, 0), chest=(8, -8, 0), head=(-22, 10, 0))   # right shoulder driven forward
    follow = P(slash, ARMS(upper_arm_R=(-0.6, -0.65, -0.45), forearm_R=(-0.62, -0.68, -0.38),   # carried through, still straight
                           upper_arm_L=(0.1, -0.95, -0.2), forearm_L=(0.08, -0.97, -0.18)),
               spine=(20, 10, 0), chest=(6, 6, 0))
    wide = [("weapon", (-0.6, -0.7, 0.3), (0, 0, 1)), ("weapon.L", (0.6, -0.7, 0.3), (0, 0, 1))]
    back = [("weapon", (0, -1, 0.2), (1, 0, 0))]
    L = LUNGE_KILL
    out.append(clip(rig, "Attack", [
        K(1, g, drop=GD), K(7, wind, (0, 0.02, 0), None, GD + 0.06,
                            aims=[("weapon", (0.7, 0.2, 0.68), (0, 0, 1)), ("weapon.L", (0.15, -0.85, 0.5), (0, 0, 1))]),
        K(12, whirl, (0, L * 0.45, 0), None, GD + 0.06, aims=wide),
        K(16, slash, (0, L, 0), None, GD + 0.06, aims=[("weapon", "target", T_SLASH)] + wide[1:]),
        K(20, follow, (0, L - 0.02, 0), None, GD + 0.06,
          aims=[("weapon", (-0.6, -0.4, -0.3), (0, 0, 1)), ("weapon.L", (-0.4, -0.9, 0.0), (0, 0, 1))]),
        K(28, coil, (0, L * 0.5, 0), None, GD + 0.04, aims=back),
        K(38, g, (0, 0, 0), None, GD)], aims=hold, flowing=True))
    # Draw (sheet "ポーン | 双剣抜刀モーション（両腰・腕クロス・詳細コマ割り）", 16 beats): 構え / 気配を感じる / 両手を腰へ
    # (左手→右腰・右手→左腰) / 柄に手をかける / しっかりと握る / 腕をクロスさせる / クロス状態(タメ) / わずかに引き出す /
    # さらに引き抜く / 同時に抜き始める / 剣が鞘から離れる / 腕が開く(左右へ) / 抜刀完了(両剣を展開) / 斬撃の構え /
    # 斬撃の軌跡 / フィニッシュ. Both blades come out together, the arms still crossed, then swing apart.
    free = P(STAND, ARMS(upper_arm_R=(-0.3, -0.05, -0.95), forearm_R=(-0.2, -0.4, -0.9), upper_arm_L=(0.3, -0.05, -0.95), forearm_L=(0.2, -0.4, -0.9)),
             spine=(3, 0, 0), head=(-2, 0, 0))
    sense = add(free, P(spine=(6, 0, 0), head=(-6, 8, 0), thigh_L=(8, 0, 0), shin_L=(-14, 0, 0), shin_R=(-10, 0, 0)))
    crossed = add(rest, P(spine=(10, 0, 0), chest=(4, 0, 0), head=(-6, 0, 0), thigh_L=(14, 0, 4), shin_L=(-24, 0, 0), thigh_R=(4, 0, -4), shin_R=(-18, 0, 0)))
    tame = add(crossed, P(spine=(4, 0, 0), chest=(-3, 0, 0)))
    pulling = add(crossed, P(ARMS(upper_arm_R=(-0.1, -0.55, -0.83), forearm_R=(0.85, -0.45, -0.1),
                                  upper_arm_L=(0.1, -0.6, -0.8), forearm_L=(-0.85, -0.5, -0.05)), spine=(-2, 0, 0)))
    opened = P(STAND, ARMS(upper_arm_R=(-0.8, -0.35, -0.45), forearm_R=(-0.85, -0.45, 0.2), upper_arm_L=(0.8, -0.35, -0.45), forearm_L=(0.85, -0.45, 0.2)),
               spine=(8, 0, 0), chest=(-4, 0, 0), head=(-10, 0, 0))
    spread = [("weapon", (-0.9, -0.3, 0.3), (0, 0, 1)), ("weapon.L", (0.9, -0.3, 0.3), (0, 0, 1))]
    trail = [("weapon", (0.6, -0.8, 0.1), (0, 0, 1)), ("weapon.L", (-0.6, -0.8, 0.1), (0, 0, 1))]
    swing = P(STAND, ARMS(upper_arm_R=(0.1, -0.95, -0.2), forearm_R=(0.6, -0.8, 0.0), upper_arm_L=(-0.1, -0.95, -0.2), forearm_L=(-0.6, -0.8, 0.0)),
              spine=(14, 0, 0), chest=(4, 0, 0), head=(-14, 0, 0))   # both blades swept in across the front (斬撃の軌跡)
    out.append(clip(rig, "Draw", [
        K(1, free, aims=FREE), K(6, sense, drop=0.03, aims=FREE), K(12, crossed, drop=0.06, aims=FREE), K(16, crossed, drop=0.07, aims=FREE),
        K(20, add(crossed, P(chest=(2, 0, 0))), drop=0.07, aims=FREE), K(24, tame, drop=0.08, aims=FREE), K(30, tame, drop=0.08, aims=FREE),
        K(34, pulling, drop=0.07, aims=FREE), K(38, pulling, drop=0.06, aims=FREE),
        K(42, add(pulling, P(spine=(-4, 0, 0))), drop=0.04, aims=[("weapon", (0.85, -0.4, 0.3), (0, 0, 1)), ("weapon.L", (-0.85, -0.4, 0.3), (0, 0, 1))]),
        K(46, opened, drop=0.02, aims=spread), K(50, add(opened, P(spine=(-4, 0, 0))), drop=0.03, aims=spread),
        K(54, g, drop=GD, aims=hold), K(58, swing, drop=GD + 0.04, aims=trail), K(62, opened, drop=GD, aims=spread),
        K(70, g, drop=GD)], aims=hold, flowing=True))
    hitb = [("weapon", "target", T_GUARD)]
    out.append(clip(rig, "AttackBlocked", [
        K(1, g, drop=GD), K(8, coil, drop=GD + 0.06, aims=back),
        K(16, stab, (0, LUNGE_BLOCKED, 0), drop=GD + 0.06, aims=hitb),
        K(22, stab, (0, LUNGE_BLOCKED + 0.01, 0), drop=GD + 0.06, aims=hitb),
        K(29, coil, (0, LUNGE_BLOCKED * 0.4, 0), drop=GD + 0.05, aims=back), K(40, g, drop=GD)], aims=hold, flowing=True))
    # Dodge (design sheet "回避からの反撃"): as the opponent's spin slash comes in, the pawn ducks and sways out of
    # its line to the left; the blade passes through empty air on frame 16 and the pawn springs back to guard.
    duck = P({"thigh.L": (50, 0, 20), "shin.L": (-80, 0, 0), "foot.L": (30, 0, 0),
              "thigh.R": (10, 0, -30), "shin.R": (-30, 0, 0), "foot.R": (20, 0, 0)},
             GUARD_ARMS, spine=(30, 0, 18), chest=(8, 0, 8), head=(-24, 0, -10))
    out.append(clip(rig, "Dodge", [
        K(1, g, drop=GD), K(8, duck, (DODGE * 0.6, 0.05, 0), drop=GD + 0.14),
        K(14, duck, (DODGE, 0.1, 0), drop=GD + 0.2), K(22, duck, (DODGE, 0.12, 0), drop=GD + 0.2),
        K(28, duck, (DODGE * 0.85, 0.1, 0), drop=GD + 0.16),   # stays out of line until both blades have passed
        K(36, g, (0.06, 0.02, 0), drop=GD), K(42, g, drop=GD)], aims=hold, flowing=True))
    # Defence clips start together with the attacker's Attack: its point lands on frame 16, so the defender
    # crosses its daggers in an X before the chest by ~9, braces, and takes the blow on 17.
    xguard = P({"thigh.L": (26, 0, 4), "shin.L": (-42, 0, 0), "foot.L": (14, 0, 0),
                "thigh.R": (-12, 0, -4), "shin.R": (-22, 0, 0), "foot.R": (30, 0, 0)},
               ARMS(upper_arm_R=(-0.35, -0.55, -0.75), forearm_R=(0.55, -0.75, 0.35),
                    upper_arm_L=(0.35, -0.55, -0.75), forearm_L=(-0.55, -0.75, 0.35)),
               spine=(14, 0, 0), chest=(4, 0, 0), neck=(-6, 0, 0), head=(-10, 0, 0), hips=(0, 15, 0))
    braced = add(xguard, P(spine=(4, 0, 0), head=(4, 0, 0)))
    absorbed = add(xguard, P(spine=(-10, 0, 0), head=(-10, 0, 0)))   # the X is driven back into the chest
    x = [("weapon", (0.6, -0.3, 0.75), (0, -1, 0)), ("weapon.L", (-0.6, -0.3, 0.75), (0, -1, 0))]
    out.append(clip(rig, "Block", [
        K(1, g, drop=GD), K(9, xguard, aims=x), K(15, braced, aims=x), K(16, braced, aims=x),
        K(18, absorbed, (0, 0.06, 0), aims=x), K(21, braced, (0, 0.07, 0), aims=x),
        K(26, xguard, (0, 0.04, 0), aims=x), K(36, g, drop=GD)], aims=hold, flowing=True))
    # Hit (never a body hit - that kills): the blow lands on the X and drives the piece back off balance
    reel = add(absorbed, P(spine=(-14, 0, 5), head=(-12, 8, 0),
                           thigh_L=(-14, 0, 0), shin_L=(-6, 0, 0), thigh_R=(12, 0, 0), shin_R=(-30, 0, 0)))
    knee = P({"thigh.L": (70, 0, 10), "shin.L": (-110, 0, 0), "foot.L": (30, 0, 0), "thigh.R": (10, 0, -12),
              "shin.R": (-120, 0, 0), "foot.R": (50, 0, 0)}, GUARD_ARMS, spine=(30, 0, -6), chest=(8, 0, 0), head=(-10, 0, 0))
    rise = P({"thigh.L": (50, 0, 12), "shin.L": (-80, 0, 0), "foot.L": (20, 0, 0), "thigh.R": (0, 0, -12),
              "shin.R": (-60, 0, 0), "foot.R": (30, 0, 0)}, GUARD_ARMS, spine=(22, 0, 0), head=(-14, 0, 0))
    out.append(clip(rig, "Hit", [
        K(1, g, drop=GD), K(9, xguard, aims=x), K(15, braced, aims=x), K(16, braced, aims=x),
        K(18, reel, (0, 0.12, 0), (-5, 0, 2), aims=x), K(22, add(reel, P(spine=(8, 0, -3))), (0, 0.17, 0), aims=x),
        K(27, add(reel, P(spine=(-6, 0, 8), thigh_R=(-10, 0, 0))), (0.02, 0.2, 0), (-4, 0, 4), aims=x),   # balance lost
        K(33, knee, (0.02, 0.21, 0), aims=x), K(38, knee, (0.02, 0.21, 0)),                             # down on a knee
        K(44, rise, (0.01, 0.17, 0)), K(50, g, (0, 0.1, 0), drop=GD), K(58, g, drop=GD)], aims=hold, flowing=True))
    # Death: crosses the daggers, the guard is smashed open (arms flung wide), staggers, kneels, pitches forward
    knocked = add(g, P(ARMS(upper_arm_L=(0.85, -0.1, -0.5), forearm_L=(0.6, -0.6, 0.5),
                            upper_arm_R=(-0.85, -0.1, -0.5), forearm_R=(-0.6, -0.6, 0.5)),
                       spine=(-22, 0, 6), chest=(-10, 0, 0), head=(-24, 14, 0), hips=(0, -15, 0),
                       thigh_L=(-12, 0, 0), shin_L=(-4, 0, 0), thigh_R=(14, 0, 0), shin_R=(-26, 0, 0)))
    flung = add(xguard, P(ARMS(upper_arm_L=(0.85, -0.15, -0.5), forearm_L=(0.75, -0.55, 0.35),
                               upper_arm_R=(-0.85, -0.15, -0.5), forearm_R=(-0.75, -0.55, 0.35)), spine=(2, 0, 0)))
    wide = [("weapon", (-0.8, -0.3, 0.5), (0, 0, 1)), ("weapon.L", (0.8, -0.3, 0.5), (0, 0, 1))]
    kneel = P({"thigh.L": (85, 0, 6), "shin.L": (-120, 0, 0), "foot.L": (30, 0, 0),
               "thigh.R": (20, 0, -6), "shin.R": (-125, 0, 0), "foot.R": (50, 0, 0)},
              ARMS(upper_arm_R=(-0.2, -0.2, -0.95), forearm_R=(-0.1, -0.5, -0.85),
                   upper_arm_L=(0.2, -0.2, -0.95), forearm_L=(0.1, -0.5, -0.85)),
              spine=(28, 0, -6), chest=(12, 0, 0), head=(30, -15, 0))
    stagger = add(knocked, P(spine=(18, 0, -8), head=(20, -10, 0), thigh_L=(30, 0, 0), shin_L=(-40, 0, 0)))
    flat = P({"thigh.L": (10, 0, 6), "shin.L": (-20, 0, 0), "thigh.R": (6, 0, -6), "shin.R": (-14, 0, 0)},
             ARMS(upper_arm_R=(-0.3, -0.25, 0.92), forearm_R=(-0.2, -0.45, 0.87),
                  upper_arm_L=(0.3, -0.25, 0.92), forearm_L=(0.2, -0.45, 0.87)),
             spine=(4, 0, 0), head=(-30, 30, 0))
    out.append(clip(rig, "Death", [
        K(1, g, drop=GD), K(8, xguard, aims=x), K(11, braced, aims=x),
        K(14, flung, aims=wide), K(17, knocked, (0, 0.09, 0), (-8, 0, 4), aims=wide),
        K(24, stagger, (0, 0.12, 0), aims=FREE),
        K(34, kneel, (0, 0.1, 0), aims=FREE), K(40, kneel, (0, 0.08, 0), (8, 0, 0), 0.52, FREE),
        K(50, flat, (0, -0.08, 0.02), (82, 0, 0), 0.1, FREE), K(54, flat, (0, -0.09, 0.035), (78, 0, 0), 0.1, FREE),
        K(60, flat, (0, -0.09, 0.02), (82, 0, 0), 0.1, FREE), K(78, flat, (0, -0.09, 0.02), (82, 0, 0), 0.1, FREE)],
        aims=hold))
    # DeathCut: cut down in passing (the rook's Iai): the X is still up when the blade goes through on frame 16-17,
    # the pawn folds over it and sinks - arms kept in, so its blades never swing out into the one passing by
    folded = add(reel, P(spine=(30, 0, 0), chest=(10, 0, 0), head=(20, 0, 0)))
    out.append(clip(rig, "DeathCut", [
        K(1, g, drop=GD), K(8, xguard, aims=x), K(11, braced, aims=x), K(16, braced, aims=x),
        K(19, add(braced, P(spine=(-10, 0, 4), head=(-14, 6, 0))), (0, 0.03, 0), aims=x),
        K(26, folded, (0, 0.04, 0), aims=x), K(36, kneel, (0, 0.04, 0), aims=x), K(42, kneel, (0, 0.03, 0), (8, 0, 0), 0.52, x),
        K(52, flat, (0, -0.08, 0.02), (82, 0, 0), 0.1, x), K(56, flat, (0, -0.09, 0.035), (78, 0, 0), 0.1, x),
        K(62, flat, (0, -0.09, 0.02), (82, 0, 0), 0.1, x), K(80, flat, (0, -0.09, 0.02), (82, 0, 0), 0.1, x)], aims=hold))
    # Clash / Clash2 (design sheet "斬り合い①②"): both pieces play it at once, PAWN_DUEL apart. A wide slash swung in
    # from the side - right blades, then left blades - the edges meet at the midpoint on frame 15 in a shower of
    # sparks, are beaten back, and both fall back to guard.
    draw_back = P(STAND, ARMS(upper_arm_R=(-0.5, 0.1, -0.86), forearm_R=(-0.45, -0.6, 0.65), upper_arm_L=(0.3, -0.3, -0.9),
                              forearm_L=(0.1, -0.95, 0.2)), spine=(14, 14, 0), chest=(4, 6, 0), head=(-14, -8, 0))   # a short cock
    cut_in = P({"thigh.L": (36, 0, 12), "shin.L": (-46, 0, 0), "foot.L": (10, 0, 0),
                "thigh.R": (-14, 0, -12), "shin.R": (-26, 0, 0), "foot.R": (30, 0, 0)},
               ARMS(upper_arm_R=(-0.35, -0.9, -0.1), forearm_R=(0.3, -0.95, 0.05), upper_arm_L=(0.6, -0.25, -0.76),
                    forearm_L=(0.35, -0.9, -0.25)), spine=(20, -12, 0), chest=(6, -8, 0), head=(-18, 8, 0))
    beaten = add(cut_in, P(ARMS(upper_arm_R=(-0.8, -0.3, -0.4), forearm_R=(-0.8, -0.2, 0.4)), spine=(-14, 10, 0), head=(-8, 0, 0)))
    meet = [("weapon", "target", T_CLASH)]
    def exchange(name, m, blade, other):
        out.append(clip(rig, name, [
            K(1, g, drop=GD), K(7, m(draw_back), drop=GD + 0.04, aims=[(blade, (-0.9 * other, 0.4, 0.1), (0, 0, 1))]),
            K(13, m(cut_in), (0, LUNGE_CLASH, 0), drop=GD + 0.06, aims=[(blade, "target", T_CLASH)]),
            K(15, m(cut_in), (0, LUNGE_CLASH, 0), drop=GD + 0.06, aims=[(blade, "target", T_CLASH)]),
            K(19, m(beaten), (0, LUNGE_CLASH * 0.5 + 0.03, 0), drop=GD + 0.04, aims=[(blade, (-0.9 * other, -0.3, 0.3), (0, 0, 1))]),
            K(28, g, (0, 0.01, 0), drop=GD), K(36, g, drop=GD)], aims=hold, flowing=True))
    exchange("Clash", lambda p: p, "weapon", 1)
    exchange("Clash2", mirror, "weapon.L", -1)
    # Combo / Heavy / Rush (storyboard): strings of cuts, each wound up 3 frames before and landing on the guard
    # (anims T_GUARD) on its hit frame; Counter answers an attack with a parry, steps in and cuts back three times.
    low_wind = P(draw_back, ARMS(upper_arm_R=(-0.4, 0.0, -0.92), forearm_R=(-0.3, -0.6, -0.75)), spine=(18, 10, 0))
    high_wind = P(draw_back, ARMS(upper_arm_R=(-0.35, -0.3, 0.5), forearm_R=(0.1, -0.5, 0.86)), spine=(8, 8, 0), head=(-18, -4, 0))
    winds = {"side": draw_back, "up": low_wind, "down": high_wind, "spin": whirl}
    approach = {"side": (-0.7, -0.2, 0.4), "up": (-0.3, -0.5, -0.8), "down": (-0.15, -0.3, 0.94), "spin": (-0.7, -0.2, 0.4)}
    def strikes(name, keys, end, rest_loc=0.0):
        """Wind-up + cut keys for PAWN_COMBOS[name]; returns the merged, frame-sorted key list."""
        events, hits = [], []
        spun = 0
        for f, blade, style in PAWN_COMBOS[name]:
            m = (lambda q: q) if blade == "weapon" else mirror
            side = 1 if blade == "weapon" else -1
            lunge = PAWN_LUNGE.get((name, f), -0.1)
            a = approach[style]
            rot_w = (0, 0, spun + (200 if style == "spin" else 0) * side) if style == "spin" or spun else None
            if style == "spin": spun += 360 * side
            rot_h = (0, 0, spun) if spun else None
            keys.append(K(f - 3, m(winds[style]), (0, lunge * 0.6, 0), rot_w, GD + 0.04,
                          aims=[(blade, (a[0] * side, a[1], a[2]), (0, 0, 1))]))
            hits.append(K(f, m(cut_in), (0, lunge, 0), rot_h, GD + 0.06, aims=[(blade, "target", T_GUARD)]))
            events.append([f, blade])
        rot_end = (0, 0, spun) if spun else None
        keys += [K(end - 6, coil, (0, rest_loc * 0.5, 0), rot_end, GD + 0.04, aims=back), K(end, g, (0, 0, 0), rot_end, GD)]
        PAWN_EVENTS[name] = events
        byf = {}
        for k in keys + hits: byf[k["f"]] = k   # a cut always wins over a wind-up that falls on the same frame
        return [byf[f] for f in sorted(byf)]
    out.append(clip(rig, "Combo", strikes("Combo", [K(1, g, drop=GD), K(4, coil, (0, -0.03, 0), drop=GD + 0.05, aims=back)], 46),
                    aims=hold, flowing=True))
    crouch = add(coil, P(spine=(10, 0, 0), thigh_L=(10, 0, 0), shin_L=(-16, 0, 0), shin_R=(-14, 0, 0)))
    leap = P(stab, ARMS(upper_arm_R=(-0.4, 0.1, 0.9), forearm_R=(0.1, -0.2, 0.97)), spine=(0, 0, 0), head=(-20, 0, 0))
    out.append(clip(rig, "Heavy", strikes("Heavy", [
        K(1, g, drop=GD), K(6, crouch, (0, 0.03, 0), drop=GD + 0.1, aims=back), K(10, crouch, (0, 0.04, 0), drop=GD + 0.14, aims=back),
        K(13, leap, (0, -0.12, 0.1), drop=GD - 0.05, aims=[("weapon", (0, 0.3, 0.95), (1, 0, 0))])], 40), aims=hold, flowing=True))
    dash = add(stab, P(spine=(10, 0, 0)))
    out.append(clip(rig, "Rush", strikes("Rush", [
        K(1, g, drop=GD), K(4, dash, (0, -0.08, 0), drop=GD + 0.06, aims=back)], 44), aims=hold, flowing=True))
    # Rush ends with a hop back out of reach (storyboard "飛び退き")
    # Defend<Combo/Heavy/Rush>: crossed blades held up, recoiling on each hit frame of the matching string
    def defend(name, end):
        keys = [K(1, g, drop=GD), K(5, xguard, aims=x)]
        for f, blade, style in PAWN_COMBOS[name]:
            keys += [K(f, braced, (0, 0.02, 0), aims=x), K(f + 2, absorbed, (0, 0.05, 0), aims=x)]
        keys += [K(end - 6, xguard, (0, 0.04, 0), aims=x), K(end, g, drop=GD)]
        byf = {}
        for k in keys: byf[k["f"]] = k
        out.append(clip(rig, "Defend" + name, [byf[f] for f in sorted(byf)], aims=hold, flowing=True))
    defend("Combo", 46); defend("Heavy", 40); defend("Rush", 44)
    # against the mounted knight: every combo cut taken on the X; the skill's two light blows taken, then the sweep kills
    keys = [K(1, g, drop=GD), K(5, xguard, aims=x)]
    for f in KNIGHT_COMBO_FRAMES: keys += [K(f, braced, (0, 0.02, 0), aims=x), K(f + 2, absorbed, (0, 0.05, 0), aims=x)]
    keys += [K(56, xguard, (0, 0.04, 0), aims=x), K(62, g, drop=GD)]
    out.append(clip(rig, "DefendKnight", keys, aims=hold))
    keys = [K(1, g, drop=GD), K(5, xguard, aims=x)]
    for f in QUEEN_COMBO_FRAMES: keys += [K(f, braced, (0, 0.02, 0), aims=x), K(f + 2, absorbed, (0, 0.05, 0), aims=x)]
    keys += [K(QUEEN_COMBO_FRAMES[-1] + 8, xguard, (0, 0.04, 0), aims=x), K(QUEEN_COMBO_FRAMES[-1] + 16, g, drop=GD)]
    out.append(clip(rig, "DefendQueen", keys, aims=hold))
    g1, g2 = KNIGHT_SKILL_GUARD; kf = KNIGHT_SKILL_KILL
    def die_after(name, guards, kf):   # blows taken on the X, then the killing blow lands on kf
        keys = [K(1, g, drop=GD), K(8, xguard, aims=x)]
        for i, f in enumerate(guards): keys += [K(f, braced, (0, 0.02 * i, 0), aims=x), K(f + 2, absorbed, (0, 0.03 + 0.02 * i, 0), aims=x)]
        keys += [K(kf - 2, flung, (0, 0.0, 0), aims=wide), K(kf, flung, (0, 0.0, 0), aims=wide), K(kf + 3, knocked, (0, 0.1, 0), (-8, 0, 4), aims=wide),
                 K(kf + 8, stagger, (0, 0.15, 0), aims=FREE), K(kf + 18, kneel, (0, 0.13, 0), aims=FREE),
                 K(kf + 24, kneel, (0, 0.11, 0), (8, 0, 0), 0.52, FREE),
                 K(kf + 34, flat, (0, -0.06, 0.02), (82, 0, 0), 0.1, FREE), K(kf + 38, flat, (0, -0.07, 0.035), (78, 0, 0), 0.1, FREE),
                 K(kf + 44, flat, (0, -0.07, 0.02), (82, 0, 0), 0.1, FREE), K(kf + 60, flat, (0, -0.07, 0.02), (82, 0, 0), 0.1, FREE)]
        out.append(clip(rig, name, keys, aims=hold))
    die_after("DieToKnightMace", KNIGHT_MACE_GUARD, KNIGHT_MACE_KILL)
    die_after("DieToKnightSweep", (), 24)   # knight_anims.py Sweep: braced with the X, swept away on frame 24
    out.append(clip(rig, "DieToKnightSkill", [
        K(1, g, drop=GD), K(8, xguard, aims=x), K(g1, braced, aims=x), K(g1 + 2, absorbed, (0, 0.05, 0), aims=x),
        K(g2, braced, (0, 0.03, 0), aims=x), K(g2 + 2, absorbed, (0, 0.07, 0), aims=x),
        K(kf - 2, flung, (0, 0.0, 0), aims=wide), K(kf, flung, (0, 0.0, 0), aims=wide), K(kf + 3, knocked, (0, 0.1, 0), (-8, 0, 4), aims=wide),
        K(kf + 8, stagger, (0, 0.15, 0), aims=FREE), K(kf + 18, kneel, (0, 0.13, 0), aims=FREE),
        K(kf + 24, kneel, (0, 0.11, 0), (8, 0, 0), 0.52, FREE),
        K(kf + 34, flat, (0, -0.06, 0.02), (82, 0, 0), 0.1, FREE), K(kf + 38, flat, (0, -0.07, 0.035), (78, 0, 0), 0.1, FREE),
        K(kf + 44, flat, (0, -0.07, 0.02), (82, 0, 0), 0.1, FREE), K(kf + 60, flat, (0, -0.07, 0.02), (82, 0, 0), 0.1, FREE)], aims=hold))
    # Counter: the opponent's thrust (frame 16) is met on the crossed blades and swept aside, the pawn steps in
    # and cuts back three times; Parried is the opponent's side of it - thrust, swept aside, three cuts on its guard,
    # and a stagger
    sweep = P(xguard, ARMS(upper_arm_R=(-0.85, -0.3, -0.3), forearm_R=(-0.8, -0.5, 0.2), upper_arm_L=(0.6, -0.4, -0.6),
                           forearm_L=(0.5, -0.8, 0.1)), spine=(10, 14, 0))
    out.append(clip(rig, "Counter", strikes("Counter", [
        K(1, g, drop=GD), K(9, xguard, aims=x), K(16, braced, aims=x),
        K(19, sweep, (0, 0.02, 0), aims=[("weapon", (-0.95, -0.2, 0.2), (0, 0, 1)), ("weapon.L", (0.5, -0.8, 0.2), (0, 0, 1))]),
        K(22, dash, (0, -0.05, 0), drop=GD + 0.06, aims=back)], 46), aims=hold, flowing=True))
    PAWN_EVENTS["Counter"] = [[16, "x"]] + PAWN_EVENTS["Counter"]   # the parried thrust lands on the X first
    knocked_aside = add(stab, P(ARMS(upper_arm_R=(-0.8, -0.3, -0.4), forearm_R=(-0.8, -0.2, 0.4)), spine=(-14, 10, 0)))
    pk = [K(1, g, drop=GD), K(8, coil, drop=GD + 0.06, aims=back),
          K(16, stab, (0, LUNGE_BLOCKED, 0), drop=GD + 0.06, aims=[("weapon", "target", T_GUARD)]),
          K(19, knocked_aside, (0, LUNGE_BLOCKED * 0.5, 0), drop=GD + 0.04, aims=[("weapon", (-0.9, -0.3, 0.3), (0, 0, 1))]),
          K(23, xguard, (0, 0.02, 0), aims=x)]
    for f, blade, style in PAWN_COMBOS["Counter"]:
        pk += [K(f, braced, (0, 0.03, 0), aims=x), K(f + 2, absorbed, (0, 0.07, 0), aims=x)]
    pk += [K(42, add(reel, P(spine=(6, 0, 0))), (0, 0.14, 0), (-4, 0, 2), aims=x), K(54, g, drop=GD)]
    out.append(clip(rig, "Parried", pk, aims=hold, flowing=True))
    # Victory: both daggers thrust overhead, crossed
    def cheer(lift):
        return P(STAND, ARMS(upper_arm_R=(-0.4, -0.1, 0.9 + lift), forearm_R=(0.25, -0.1, 0.96),
                             upper_arm_L=(0.4, -0.1, 0.9 + lift), forearm_L=(-0.25, -0.1, 0.96)),
                 spine=(-6, 0, 0), chest=(-8, 0, 0), head=(-18, 0, 0))
    sky = [("weapon", (0.35, -0.1, 0.93), (0, -1, 0)), ("weapon.L", (-0.35, -0.1, 0.93), (0, -1, 0))]
    down = [("weapon", (-0.2, 0.3, -0.93), (1, 0, 0)), ("weapon.L", (0.2, 0.3, -0.93), (1, 0, 0))]
    out.append(clip(rig, "Victory", [
        K(1, g, drop=GD), K(10, cheer(0), drop=-0.02, aims=sky),
        K(16, cheer(0.4), aims=sky), K(24, cheer(-0.25), aims=sky), K(30, cheer(0), aims=sky),
        K(36, grip, drop=0.02, aims=down), K(42, rest, aims=FREE), K(54, rest, aims=FREE)], aims=hold))
    # where the wrists rest on the hilts (IK) and the daggers sit in the scabbards, per clip
    sheathed = {"Idle": ([(1, 1)], [(1, 1)]), "Walk": ([(1, 1)], [(1, 1)]),
                "Draw": ({"R": [(1, 0), (8, 0), (14, 1), (38, 1), (44, 0)], "L": [(1, 0), (8, 0), (14, 1), (38, 1), (44, 0)]},   # both together
                         {"R": [(1, 1), (32, 1), (36, 0.85), (40, 0.55), (44, 0)], "L": [(1, 1), (32, 1), (36, 0.85), (40, 0.55), (44, 0)]}),
                "Victory": ([(1, 0), (32, 0), (36, 1)], [(1, 0), (34, 0), (36, 1)])}
    for a in out:
        ik, sh = sheathed.get(a.name.split("|")[1], (None, [(1, 0)]))
        if ik: hilt_ik(rig, a, ik)
        sheath_pass(rig, a, sh)   # keys every dagger frame (also where w = 0) so clips never inherit a sheathed dagger
        side_pts = lambda sd, sh=sh: sh[sd] if isinstance(sh, dict) else sh
        pin_r = lambda f, s_=side_pts("R"): ramp(s_, f) > 0
        pin_l = lambda f, s_=side_pts("L"): ramp(s_, f) > 0
        tip = (0.1 + DAGGER_L) * rig.get("piece_scale", 1.0)
        natural_wrist(rig, a, "hand.R", "weapon", pin_r, tip, edge=True); natural_wrist(rig, a, "hand.L", "weapon.L", pin_l, tip, edge=True)
    return out

CLIPS = {"Pawn": pawn_clips}

def animate(rigs):
    for a in list(bpy.data.actions): bpy.data.actions.remove(a)
    bpy.context.scene.render.fps = FPS
    made = {}
    for name, (rig, mesh) in rigs.items():
        if name in CLIPS:
            made[name] = CLIPS[name](rig)
    return made
