# Build -> animate -> export (Unity FBX with every clip + GLB for WebPreview). Run inside Blender:
#   exec(open(CHESS + "/BlenderSource/export.py", encoding="utf-8").read())
import os as _os, bpy as _bpy
# the repository root: $CHESS_ROOT, else the folder above the open .blend / this script (no machine paths in the repo)
CHESS = (_os.environ.get("CHESS_ROOT") or (_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))) if "__file__" in globals() else "")
         or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)) or ".").replace("\\", "/")

def scrub_user(path):
    """FBX files record the path they were written to: blank out the home folder's name before it is committed."""
    u = _os.path.basename(_os.path.expanduser("~")).encode()
    b = open(path, "rb").read()
    if u and u in b: open(path, "wb").write(b.replace(u, b"x" * len(u)))   # same length: the binary FBX stays valid

import bpy, os
SRC = CHESS + "/BlenderSource/"
exec(open(SRC + "warriors.py", encoding="utf-8").read())
exec(open(SRC + "knight.py", encoding="utf-8").read())
exec(open(SRC + "bishop.py", encoding="utf-8").read())
exec(open(SRC + "rook.py", encoding="utf-8").read())
exec(open(SRC + "queen.py", encoding="utf-8").read())
exec(open(SRC + "king.py", encoding="utf-8").read())
exec(open(SRC + "anims.py", encoding="utf-8").read())
exec(open(SRC + "knight_anims.py", encoding="utf-8").read())
exec(open(SRC + "bishop_anims.py", encoding="utf-8").read())
exec(open(SRC + "rook_anims.py", encoding="utf-8").read())
exec(open(SRC + "queen_anims.py", encoding="utf-8").read())
exec(open(SRC + "king_anims.py", encoding="utf-8").read())
WEB = CHESS + "/WebPreview/models"
os.makedirs(WEB, exist_ok=True)

SLOT_ORDER = ("PieceBody", "Trim", "Shadow", "Glow")   # Unity's ChessSceneBuilder assigns materials by this slot order

def fix_slot_order(mesh):
    me = mesh.data
    old = [m.name if m else "" for m in me.materials]
    order = [n for n in SLOT_ORDER if n in old] + [n for n in old if n not in SLOT_ORDER]
    remap = {old.index(n): i for i, n in enumerate(order)}
    mats = [me.materials[old.index(n)] for n in order]
    idx = [remap[p.material_index] for p in me.polygons]
    me.materials.clear()
    for m in mats: me.materials.append(m)
    for p, i in zip(me.polygons, idx): p.material_index = i

def export_piece(name, rig, mesh):
    """Only this piece's own clips go out: every piece shares bone names (hips, chest...), so exporting
    "all actions" also baked the pawn's clips onto the knight. Each own action becomes one NLA track
    (track name = action name) and both exporters write just the tracks."""
    fix_slot_order(mesh)
    loc = rig.location.copy()
    rig.location = (0, 0, 0)
    rig.animation_data_create()
    rig.animation_data.action = None
    for b in rig.pose.bones: b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
    ad = rig.animation_data
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    for act in sorted((a for a in bpy.data.actions if a.name.startswith(name + "|")), key=lambda a: a.name):
        tr = ad.nla_tracks.new(); tr.name = act.name
        st = tr.strips.new(act.name, int(act.frame_range[0]), act)
        st.name = act.name
        tr.mute = True   # muted tracks still export; they just do not stack on top of each other in the viewport
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); mesh.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=f"{WEB}/{name}.glb", export_format='GLB', use_selection=True,
                              export_animations=True, export_animation_mode='NLA_TRACKS', export_yup=True)
    for t in ad.nla_tracks: t.mute = False
    bpy.ops.export_scene.fbx(filepath=f"{OUT}/{name}.fbx", use_selection=True, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_UNITS', bake_space_transform=False,
                             axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE',
                             object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=True,
                             bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0)
    scrub_user(f"{OUT}/{name}.fbx")
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    rig.location = loc

def export_walk_speed(name, rig, samples=96):
    """Forward speed curve that keeps the planted foot locked to the board while Walk plays in place.
    The game / viewer advances the piece by speed[phase] instead of a constant rate -> no foot sliding."""
    import json
    act = bpy.data.actions.get(f"{name}|Walk")
    if not act: return
    rig.animation_data.action = act; sc = bpy.context.scene
    f0, f1 = act.frame_range
    fb = STANCE_FEET.get(name, "foot")
    def feet():
        return {s: ((rig.pose.bones[f"{fb}.{s}"].head + rig.pose.bones[f"{fb}.{s}"].tail) / 2).copy() for s in "LR"}
    pts = []
    for i in range(samples + 1):
        fr = f0 + (f1 - f0) * i / samples
        sc.frame_set(int(fr), subframe=fr - int(fr)); pts.append(feet())
    dt = (f1 - f0) / samples / sc.render.fps
    speed = []
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        # stance by phase, not by height: L heel-strikes on the first key and carries the weight for the
        # first half, R for the second (height tests flickered at the hand-over and left the feet skating)
        s = "L" if i < samples // 2 else "R"
        speed.append(round((b[s].y - a[s].y) / dt, 4))
    json.dump({"clip": "Walk", "cycleSeconds": (f1 - f0) / sc.render.fps, "speed": speed},
              open(f"{WEB}/{name}_walk.json", "w"))
    rig.animation_data.action = None
    print(name, "walk: mean speed", round(sum(speed) / len(speed), 3), "max", max(speed))

rigs = build()
made = animate(rigs)
for n, (rig, mesh) in rigs.items():
    export_walk_speed(n, rig)
    export_piece(n, rig, mesh)
    print(n, [a.name for a in made.get(n, [])])
import json
json.dump(PAWN_EVENTS, open(f"{WEB}/Pawn_events.json", "w"))   # hit frames of the pawn's strings (sparks)
bpy.ops.wm.save_as_mainfile(filepath=SRC + "warriors.blend")
