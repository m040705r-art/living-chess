# Preview render: white set (rest pose) in front, black set (posed to prove the rig) behind. Run after chess_pieces.py.
import os as _os, bpy as _bpy
# the repository root: $CHESS_ROOT, else the folder above the open .blend / this script (no machine paths in the repo)
CHESS = (_os.environ.get("CHESS_ROOT") or (_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))) if "__file__" in globals() else "")
         or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)) or ".").replace("\\", "/")
import bpy, math, sys
from mathutils import Vector, Euler
out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else CHESS + "/BlenderSource/preview.png"
sc = bpy.context.scene
for rig, mesh_ob in _rigs:
    r2 = rig.copy(); r2.data = rig.data; sc.collection.objects.link(r2)
    m2 = mesh_ob.copy(); m2.data = mesh_ob.data.copy(); sc.collection.objects.link(m2)
    m2.parent = r2; m2.modifiers["Armature"].object = r2
    i = m2.data.materials.find("PieceBody"); m2.data.materials[i] = bpy.data.materials["PieceBody_Black"]
    r2.location.y = 0.9
    pb = r2.pose.bones
    pb["UpperArm.R"].rotation_mode = pb["ForeArm.R"].rotation_mode = 'XYZ'
    pb["UpperArm.R"].rotation_euler = (math.radians(-70), 0, 0)
    pb["ForeArm.R"].rotation_euler = (math.radians(-40), 0, 0)
    pb["UpperArm.L"].rotation_mode = 'XYZ'; pb["UpperArm.L"].rotation_euler = (math.radians(30), 0, math.radians(20))
    pb["Leg.L"].rotation_mode = 'XYZ'; pb["Leg.L"].rotation_euler = (math.radians(30), 0, 0)
    pb["Head"].rotation_mode = 'XYZ'; pb["Head"].rotation_euler = (0, 0, math.radians(25))
    pb["Spine"].rotation_mode = 'XYZ'; pb["Spine"].rotation_euler = (math.radians(-8), 0, 0)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam)
cam.location = (0.9, -4.6, 2.1); cam.rotation_euler = Euler((math.radians(72), 0, math.radians(10)))
cam.data.lens = 40; sc.camera = cam
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_shadows = True; sh.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = 1400, 800
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
