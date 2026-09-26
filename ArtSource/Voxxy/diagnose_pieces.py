"""Print how each mesh piece is being assigned to a bone.

Run headless:
    blender --background --python ArtSource/Voxxy/diagnose_pieces.py -- <quad.fbx>
"""

import collections
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_rig  # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    src = args[0] if args else os.path.join(HERE, "Voxxy_quad.fbx")

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=src)
    mesh = [o for o in bpy.data.objects if o.type == "MESH"][0]
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    build_rig.remove_base_plate(mesh)
    co = np.array([v.co[:] for v in mesh.data.vertices])
    lm = build_rig.landmarks(co)
    comps = build_rig.components(mesh)

    print("PIECES (%d total)" % len(comps))
    for c in comps[:18]:
        cc = co[c]
        centre = cc.mean(axis=0)
        print("  %5d verts -> %-11s centre(%+.3f,%+.3f)  x %+.3f..%+.3f  z %+.3f..%+.3f" % (
            len(c), build_rig.classify_piece(centre, lm), centre[0], centre[2],
            cc[:, 0].min(), cc[:, 0].max(), cc[:, 2].min(), cc[:, 2].max()))
    if len(comps) > 18:
        rest = comps[18:]
        print("  ... %d more pieces, %d verts total" % (len(rest), sum(len(c) for c in rest)))


main()
