using System.Linq;
using UnityEditor;
using UnityEngine;

// Import rules for the Blender-made pieces (BlenderSource/export.py -> Assets/Chess/Art/Models/Pieces/*.fbx).
//  - clips arrive as "Pawn|Pawn|Attack": keep only the last part, loop Idle/Walk
//  - no imported materials: ChessPiece assigns the shared stone materials
//  - the bind-pose position of every vertex is copied into UV2 so the stone noise / crumble pattern is
//    painted ON the statue and does not swim when the skinned mesh moves
public class PieceImporter : AssetPostprocessor
{
    const string Dir = "Assets/Chess/Art/Models/Pieces/";

    void OnPreprocessModel()
    {
        if (!assetPath.StartsWith(Dir)) return;
        var mi = (ModelImporter)assetImporter;
        mi.animationType = ModelImporterAnimationType.Generic;
        mi.materialImportMode = ModelImporterMaterialImportMode.None;
        mi.importBlendShapes = false;
        mi.importCameras = false;
        mi.importLights = false;
        mi.animationCompression = ModelImporterAnimationCompression.Off;   // keyframe reduction blurred the fast blade arcs (user: 滑らかさがない)
    }

    void OnPreprocessAnimation()
    {
        if (!assetPath.StartsWith(Dir)) return;
        var mi = (ModelImporter)assetImporter;
        var clips = mi.defaultClipAnimations;
        foreach (var c in clips)
        {
            c.name = c.name.Substring(c.name.LastIndexOf('|') + 1);
            c.loopTime = c.name == "Idle" || c.name == "Walk" || c.name == "Ready";
        }
        mi.clipAnimations = clips;
    }

    void OnPostprocessModel(GameObject root)
    {
        if (!assetPath.StartsWith(Dir)) return;
        foreach (var r in root.GetComponentsInChildren<SkinnedMeshRenderer>())
        {
            var m = r.sharedMesh;
            m.SetUVs(2, m.vertices.ToList());
        }
    }
}
