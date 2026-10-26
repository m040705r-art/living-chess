import os as _os, bpy as _bpy
# the repository root: $CHESS_ROOT, else the folder above the open .blend / this script (no machine paths in the repo)
CHESS = (_os.environ.get("CHESS_ROOT") or (_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))) if "__file__" in globals() else "")
         or _os.path.dirname(_os.path.dirname(_bpy.data.filepath)) or ".").replace("\\", "/")
import sys
exec(open(CHESS + "/BlenderSource/chess_pieces.py", encoding="utf-8").read())
exec(open(CHESS + "/BlenderSource/preview.py", encoding="utf-8").read())
