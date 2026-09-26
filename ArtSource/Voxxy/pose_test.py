"""Pose the rigged mesh and render, to see whether the skinning actually holds up.

Weight statistics can't tell you if a rig works -- overlapping geometry (Voxxy's arms
hang alongside its body) makes per-region weight sums ambiguous. Deforming it and
looking is the real test.

Run headless:
    blender --background --python ArtSource/Voxxy/pose_test.py -- <rigged.fbx> [out.png]
"""

import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# Bone naming differs between the hand-built rig and Tripo's auto-rig, so each slot
# lists candidates and the first one present is used.
ALIASES = {
    "head": ["Head"],
    "armL": ["Arm.L", "L_Upperarm"],
    "armR": ["Arm.R", "R_Upperarm"],
    "legL": ["Leg.L", "L_Thigh"],
    "legR": ["Leg.R", "R_Thigh"],
    "waist": ["Chest", "Waist"],
    "shoulderL": ["Shoulder.L", "L_Clavicle"],
}

# label -> list of (slot, axis, degrees)
POSES = [
    ("rest", []),
    ("head turn + tilt", [("head", "Z", 35), ("head", "X", -20)]),
    ("arms out", [("armL", "X", -45), ("armR", "X", 45)]),
    ("legs + waist", [("legL", "X", -35), ("legR", "X", 25), ("waist", "Z", 20)]),
    ("shoulder swing", [("shoulderL", "X", -40), ("armR", "X", 30), ("head", "Z", -20)]),
]


def argv_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def setup_scene():
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = 460, 660
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.6, 0.62, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    scene.world = world

    key = bpy.data.objects.new("Key", bpy.data.lights.new("Key", type="AREA"))
    key.data.energy = 250
    key.data.size = 5
    key.location = (3, -5, 4)
    key.rotation_euler = (math.radians(50), 0, math.radians(30))
    bpy.context.collection.objects.link(key)


def load_rgba(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    return px


def main():
    args = argv_after_dashes()
    if not args:
        sys.exit("usage: ... -- <rigged.fbx> [out.png]")
    mesh_path = args[0]
    out_path = args[1] if len(args) > 1 else os.path.join(HERE, "renders", "pose_test.png")

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=mesh_path)

    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if arm is None:
        sys.exit("no armature in " + mesh_path)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]

    pts = np.array([(o.matrix_world @ v.co)[:] for o in meshes for v in o.data.vertices])
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    center, size = (lo + hi) / 2.0, hi - lo

    setup_scene()
    ortho, radius = max(size) * 1.2, max(size) * 3.0

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    ang = math.radians(25)
    cam.location = (center[0] + radius * math.sin(ang),
                    center[1] - radius * math.cos(ang),
                    center[2])
    cam.rotation_euler = (math.radians(90), 0, ang)
    bpy.context.scene.camera = cam

    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"

    tiles = []
    for label, rots in POSES:
        for pb in arm.pose.bones:
            pb.rotation_euler = (0, 0, 0)
        missing = []
        for slot, axis, deg in rots:
            pb = next((arm.pose.bones.get(n) for n in ALIASES[slot]
                       if arm.pose.bones.get(n)), None)
            if pb is None:
                missing.append(slot)
                continue
            i = "XYZ".index(axis)
            e = list(pb.rotation_euler)
            e[i] = math.radians(deg)
            pb.rotation_euler = e
        bpy.context.view_layer.update()

        tmp = os.path.join(HERE, "renders", "_pose_%s.png" % label.replace(" ", "_").replace("+", ""))
        bpy.context.scene.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        tiles.append(load_rgba(tmp))
        print("POSE %-18s %s%s" % (label,
                                   ", ".join("%s %s%+d" % r for r in rots) or "(none)",
                                   "  MISSING BONES: %s" % missing if missing else ""))

    th, tw = tiles[0].shape[:2]
    sheet = np.ones((th, tw * len(tiles), 3), dtype=np.float32)
    for i, t in enumerate(tiles):
        a = t[:, :, 3:4]
        sheet[:, i * tw:(i + 1) * tw] = t[:, :, :3] * a + 1.0 * (1 - a)

    out = np.ones(sheet.shape[:2] + (4,), dtype=np.float32)
    out[:, :, :3] = np.clip(sheet, 0, 1)
    img = bpy.data.images.new("poses", width=sheet.shape[1], height=th, alpha=True)
    img.pixels = out[::-1].ravel().tolist()
    img.file_format = "PNG"
    img.filepath_raw = out_path
    img.save()
    print("WROTE %s" % out_path)


main()
