"""Scale and seat an already-rigged FBX for Unity, without touching its rig.

Generated meshes arrive centred on the origin at unit height. Unity wants a
character standing on y=0 at real-world scale, so the transform is applied to the
top-level objects only -- a skinned mesh is a child of its armature and inherits
it, and setting the same transform on both applies it twice.

Run headless:
    blender --background --python ArtSource/Voxxy/place_for_unity.py -- <in.fbx> <out.fbx> <height_m>
"""

import os
import sys

import bpy
import numpy as np


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) < 3:
        sys.exit("usage: ... -- <in.fbx> <out.fbx> <height_m>")
    src, dst, target = args[0], args[1], float(args[2])

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=src)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not meshes:
        sys.exit("no mesh in " + src)

    pts = np.array([(o.matrix_world @ v.co)[:] for o in meshes for v in o.data.vertices])
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    height = hi[2] - lo[2]
    scale = target / height

    roots = [o for o in bpy.data.objects if o.parent is None]
    for o in roots:
        o.scale = tuple(s * scale for s in o.scale)
        o.location = (o.location[0] * scale,
                      o.location[1] * scale,
                      o.location[2] * scale - lo[2] * scale)

    quads = sum(1 for o in meshes for p in o.data.polygons if len(p.vertices) == 4)
    faces = sum(len(o.data.polygons) for o in meshes)
    print("IN  height=%.4f  bounds x %.3f..%.3f y %.3f..%.3f" % (height, lo[0], hi[0], lo[1], hi[1]))
    print("RIG armatures=%d bones=%s" % (len(arms), [len(a.data.bones) for a in arms]))
    print("MESH verts=%d faces=%d quads=%d (%.0f%%)" % (
        sum(len(o.data.vertices) for o in meshes), faces, quads, 100.0 * quads / max(faces, 1)))
    print("OUT scale=%.4f  height=%.3fm  feet at z=0  roots=%s" % (
        scale, target, [o.name for o in roots]))

    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = (arms or meshes)[0]
    bpy.ops.export_scene.fbx(
        filepath=dst,
        use_selection=True,
        apply_scale_options="FBX_SCALE_ALL",
        bake_space_transform=True,
        axis_forward="-Z",
        axis_up="Y",
        object_types={"ARMATURE", "MESH"},
        add_leaf_bones=False,
        path_mode="COPY",
        embed_textures=True,
        mesh_smooth_type="FACE",
    )
    print("WROTE %s" % dst)


main()
