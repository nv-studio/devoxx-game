"""Compare a generated mesh against the model sheet, view by view.

For each of front / left / back it renders the mesh orthographically, scales the
matching reference crop so the two subjects are the same height, and emits three
panels: the render, the reference, and a silhouette overlay. The overlay is the
honest proportion check -- magenta is reference-only, cyan is mesh-only, grey is
agreement.

Run headless:
    blender --background --python ArtSource/Voxxy/compare_reference.py -- <mesh.fbx> [out_dir]
"""

import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

REF = os.path.normpath(os.path.join(HERE, "..", "..", "Assets", "Art", "Reference"))
PANEL = (420, 620)

# label -> camera angle in degrees; the reference is the matching cut-out view,
# which must have real alpha or the silhouette comparison is meaningless.
VIEWS = [
    ("front", 0),
    ("left", 90),
    ("back", 180),
]


def argv_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def load_rgba(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    return px


def save_rgb(arr, path):
    h, w = arr.shape[:2]
    out = np.ones((h, w, 4), dtype=np.float32)
    out[:, :, :3] = np.clip(arr, 0, 1)
    img = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=True)
    img.pixels = out[::-1].ravel().tolist()
    img.file_format = "PNG"
    img.filepath_raw = path
    img.save()
    bpy.data.images.remove(img)


def bbox_of(alpha, thresh=0.5):
    ys, xs = np.where(alpha > thresh)
    return xs.min(), xs.max(), ys.min(), ys.max()


def resample(src, out_h, out_w):
    """Nearest-neighbour resize; adequate for a proportion check."""
    h, w = src.shape[:2]
    yi = np.clip((np.arange(out_h) * h / out_h).astype(int), 0, h - 1)
    xi = np.clip((np.arange(out_w) * w / out_w).astype(int), 0, w - 1)
    return src[yi][:, xi]


def fit_panel(rgba, target_h):
    """Scale so the subject is target_h tall, then centre it in a PANEL-sized frame."""
    x0, x1, y0, y1 = bbox_of(rgba[:, :, 3])
    sub = rgba[y0:y1 + 1, x0:x1 + 1]
    sh, sw = sub.shape[:2]
    scale = target_h / float(sh)
    nh, nw = int(round(sh * scale)), int(round(sw * scale))
    sub = resample(sub, nh, nw)

    pw, ph = PANEL
    frame = np.zeros((ph, pw, 4), dtype=np.float32)
    oy = (ph - nh) // 2
    ox = (pw - nw) // 2
    ys, xs = max(oy, 0), max(ox, 0)
    ye, xe = min(oy + nh, ph), min(ox + nw, pw)
    frame[ys:ye, xs:xe] = sub[ys - oy:ye - oy, xs - ox:xe - ox]
    return frame


def over_white(rgba):
    a = rgba[:, :, 3:4]
    return rgba[:, :, :3] * a + (1 - a)


def setup_scene():
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = 700, 1000
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


def main():
    args = argv_after_dashes()
    if len(args) < 2:
        sys.exit("usage: ... -- <mesh.fbx> <ref_prefix> [out_dir]")
    mesh_path, prefix = args[0], args[1]
    out_dir = args[2] if len(args) > 2 else os.path.join(HERE, "renders")
    os.makedirs(out_dir, exist_ok=True)

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=mesh_path)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]

    pts = np.array([(o.matrix_world @ v.co)[:] for o in meshes for v in o.data.vertices])
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    center, size = (lo + hi) / 2.0, hi - lo

    setup_scene()
    # ortho_scale spans the taller render axis; widen it for broad subjects.
    aspect = 1000 / 700.0
    ortho = 1.15 * max(size[2], max(size[0], size[1]) * aspect)
    radius = max(size) * 3.0
    target_h = int(PANEL[1] * 0.86)

    columns = []
    for label, deg in VIEWS:
        if not os.path.exists(os.path.join(REF, "%s_%s.png" % (prefix, label))):
            print("%-6s no reference, skipped" % label)
            continue
        ang = math.radians(deg)
        cam_data = bpy.data.cameras.new("Cam")
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
        cam = bpy.data.objects.new("Cam", cam_data)
        bpy.context.collection.objects.link(cam)
        cam.location = (center[0] + radius * math.sin(ang),
                        center[1] - radius * math.cos(ang),
                        center[2])
        cam.rotation_euler = (math.radians(90), 0, ang)
        bpy.context.scene.camera = cam

        tmp = os.path.join(out_dir, "_cmp_%s.png" % label)
        bpy.context.scene.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam, do_unlink=True)

        render = fit_panel(load_rgba(tmp), target_h)
        ref_path = os.path.join(REF, "%s_%s.png" % (prefix, label))
        ref_rgba = load_rgba(ref_path)
        if (ref_rgba[:, :, 3] > 0.5).all():
            sys.exit("reference %s has no alpha; run cut_reference.py first" % ref_path)
        reference = fit_panel(ref_rgba, target_h)

        # silhouette overlay
        rm = render[:, :, 3] > 0.5
        fm = reference[:, :, 3] > 0.5
        ov = np.ones(render.shape[:2] + (3,), dtype=np.float32)
        ov[fm & ~rm] = (0.85, 0.15, 0.6)    # reference only
        ov[rm & ~fm] = (0.1, 0.65, 0.85)    # mesh only
        ov[rm & fm] = (0.35, 0.35, 0.38)    # agreement

        iou = float((rm & fm).sum()) / max(float((rm | fm).sum()), 1.0)
        print("%-6s silhouette IoU = %.3f" % (label, iou))

        columns.append(np.concatenate([over_white(render), over_white(reference), ov], axis=0))

    sheet = np.concatenate(columns, axis=1)
    out = os.path.join(out_dir, "compare.png")
    save_rgb(sheet, out)
    print("WROTE %s  (%dx%d) -- rows: render / reference / overlay" %
          (out, sheet.shape[1], sheet.shape[0]))


main()
