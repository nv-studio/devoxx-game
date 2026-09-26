"""Render a mesh from several angles into one contact sheet, for eyeballing a result.

Run headless:
    blender --background --python ArtSource/Voxxy/render_views.py -- <mesh.fbx> [out.png] [views]

Orientation of a generated mesh is not knowable up front, so this renders evenly
spaced orthographic views around the up axis and tiles them; whichever cell is the
front view can then be identified by looking at it.
"""

import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = (400, 600)


def argv_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def import_mesh(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    else:
        sys.exit("unsupported mesh format: " + ext)
    return [o for o in bpy.data.objects if o.type == "MESH"]


def world_bounds(meshes):
    pts = []
    for o in meshes:
        pts.extend([o.matrix_world @ v.co for v in o.data.vertices])
    arr = np.array([p[:] for p in pts])
    return arr.min(axis=0), arr.max(axis=0)


def setup_world():
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.5, 0.55, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    scene.world = world

    key = bpy.data.objects.new("Key", bpy.data.lights.new("Key", type="AREA"))
    key.data.energy = 400
    key.data.size = 4
    key.location = (3, -4, 5)
    key.rotation_euler = (math.radians(45), 0, math.radians(35))
    bpy.context.collection.objects.link(key)


def render_view(angle, center, radius, height, ortho_scale, path):
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho_scale
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(cam)

    cam.location = (
        center[0] + radius * math.sin(angle),
        center[1] - radius * math.cos(angle),
        center[2] + height,
    )
    cam.rotation_euler = (math.radians(90), 0, angle)
    bpy.context.scene.camera = cam

    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)


def load_rgba(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    return px


def main():
    args = argv_after_dashes()
    if not args:
        sys.exit("usage: ... -- <mesh.fbx> [out.png] [views]")

    mesh_path = args[0]
    out_path = args[1] if len(args) > 1 else os.path.join(HERE, "renders", "views.png")
    views = int(args[2]) if len(args) > 2 else 8

    clear_scene()
    meshes = import_mesh(mesh_path)
    if not meshes:
        sys.exit("no meshes in " + mesh_path)

    lo, hi = world_bounds(meshes)
    size = hi - lo
    center = (lo + hi) / 2.0
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
    quads = sum(sum(1 for p in o.data.polygons if len(p.vertices) == 4) for o in meshes)
    faces = sum(len(o.data.polygons) for o in meshes)

    print("MESH objects=%d  verts=%d  faces=%d (quads=%d, %.0f%%)  tris=%d" % (
        len(meshes), sum(len(o.data.vertices) for o in meshes), faces, quads,
        100.0 * quads / max(faces, 1), tris))
    print("BOUNDS size x=%.3f y=%.3f z=%.3f   center=(%.3f, %.3f, %.3f)" % (
        size[0], size[1], size[2], center[0], center[1], center[2]))
    print("MATERIALS %s" % sorted({m.name for o in meshes for m in o.data.materials if m}))
    print("ARMATURES %s" % [o.name for o in bpy.data.objects if o.type == "ARMATURE"])

    setup_world()
    # ortho_scale spans the taller render axis, so a wide subject needs the
    # horizontal extent scaled by the frame's aspect or it is cropped.
    aspect = RES[1] / float(RES[0])
    ortho = 1.15 * max(size[2], max(size[0], size[1]) * aspect)
    radius = max(size) * 3.0

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tiles = []
    for i in range(views):
        angle = 2 * math.pi * i / views
        tmp = os.path.join(HERE, "renders", "_view%02d.png" % i)
        render_view(angle, center, radius, 0.0, ortho, tmp)
        tiles.append(load_rgba(tmp))
        print("  view %d/%d at %.0f deg" % (i + 1, views, math.degrees(angle)))

    cols = min(views, 4)
    rows = (views + cols - 1) // cols
    th, tw = tiles[0].shape[:2]
    sheet = np.zeros((rows * th, cols * tw, 4), dtype=np.float32)
    sheet[:, :, :3] = 0.12
    sheet[:, :, 3] = 1.0
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        a = t[:, :, 3:4]
        dst = sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw]
        dst[:, :, :3] = t[:, :, :3] * a + dst[:, :, :3] * (1 - a)

    img = bpy.data.images.new("sheet", width=cols * tw, height=rows * th, alpha=True)
    img.pixels = sheet[::-1].ravel().tolist()
    img.file_format = "PNG"
    img.filepath_raw = out_path
    img.save()
    print("WROTE %s  (%d views, %dx%d)" % (out_path, views, cols * tw, rows * th))


main()
