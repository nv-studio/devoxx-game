"""Build a rigid armature for Voxxy and bind it, then export for Unity.

Tripo's biped auto-rig fitted human proportions to a non-human character, tore the
legs into a polygon fan, and triangulated the quad mesh, so the rig is built here.

Two properties of the generated mesh drive the approach:

  * It ships with a base plate -- two large flat faces at the very bottom, together
    about 13% of the mesh's surface area. Left in, it is skinned like anything else
    and drags across the floor as a grey sheet whenever a bone moves. It is deleted.

  * It is not one watertight shell but ~40 disconnected pieces: head, torso, each
    arm, each claw and foot are already separate. That makes true rigid skinning
    correct here rather than a compromise -- a whole piece goes to one bone at weight
    1.0, so nothing stretches between bones and no joint can tear. Smooth weighting
    was tried first and is worse: it splits individual pieces across bones, and a
    uniform blur bleeds the small leg bones far up into the torso.

Bone landmarks are derived from the geometry, so this works for other characters
too. Whether the head is a separate bone is decided from the piece structure rather
than assumed: Voxxy's head is its own shell, while Biggy's helmet is fused to its
body, and a Head bone there would only tear the lens domes off the hull.

Run headless:
    blender --background --python ArtSource/Voxxy/build_rig.py -- <quad.fbx> <out.fbx>
"""

import collections
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

TARGET_HEIGHT = 1.2      # metres, standing height in Unity
PLATE_AREA_MIN = 0.01    # a face this large and this flat at the base is the plate


def argv_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def remove_base_plate(mesh):
    """Delete the flat slab Tripo bakes under the model, and any loose leftovers."""
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.faces.ensure_lookup_table()

    zs = [v.co.z for v in bm.verts]
    zmin, H = min(zs), max(zs) - min(zs)

    doomed = [f for f in bm.faces
              if abs(f.normal.z) > 0.95
              and f.calc_center_median().z < zmin + 0.02 * H
              and f.calc_area() > PLATE_AREA_MIN]
    area = sum(f.calc_area() for f in doomed)

    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")

    bm.to_mesh(mesh.data)
    bm.free()
    mesh.data.update()
    print("BASEPLATE removed %d faces (area %.4f), %d loose verts" % (len(doomed), area, len(loose)))


def find_head(co, comps):
    """Decide whether the character has a separately-modelled head.

    The narrowest-cross-section test that works for a necked character finds
    nothing meaningful on a blob whose helmet is part of the hull, so this asks the
    mesh instead: is there a large piece sitting above the torso? Small high pieces
    (lens domes, antennae) are not heads and must ride with the body.
    """
    sizes = [len(c) for c in comps]
    torso = comps[int(np.argmax(sizes))]
    torso_mid = co[torso][:, 2].mean()

    best, best_size = None, 0
    for c in comps:
        if c is torso:
            continue
        if co[c][:, 2].mean() > torso_mid and len(c) > best_size:
            best, best_size = c, len(c)

    if best is None or best_size < 0.25 * len(torso):
        print("  HEAD none -- largest piece above torso is %d verts vs torso %d (fused)"
              % (best_size, len(torso)))
        return None
    neck_z = float(co[best][:, 2].min())
    print("  HEAD separate piece, %d verts, neck at z=%.4f" % (best_size, neck_z))
    return neck_z


def landmarks(co, comps):
    """Derive the character's proportions from the vertex cloud and its pieces."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    zmin, zmax = z.min(), z.max()
    H = zmax - zmin
    ax_max = np.abs(x).max()

    head_z = find_head(co, comps)
    has_head = head_z is not None
    # With no head, nothing is above the "neck", so the whole hull is torso.
    neck_z = head_z if has_head else zmax + 1e-6

    # Exclude the torso shell: on a wide-bodied character the hull is broader than
    # the arms, so a pure |x| test picks up helmet vertices and puts the shoulder
    # joint up inside the head.
    torso = comps[int(np.argmax([len(c) for c in comps]))]
    in_torso = np.zeros(len(co), dtype=bool)
    in_torso[torso] = True

    arm_sel = (z < neck_z) & (np.abs(x) > 0.55 * ax_max) & ~in_torso
    arm_x = float(np.abs(x[arm_sel]).mean())
    arm_top = float(np.percentile(z[arm_sel], 99))
    arm_bot = float(z[arm_sel].min())

    leg_sel = (z < zmin + 0.13 * H) & (np.abs(x) <= 0.55 * ax_max) & ~in_torso
    leg_x = float(np.abs(x[leg_sel & (np.abs(x) > 0.01)]).mean())
    leg_top = float(np.percentile(z[leg_sel], 88))

    lm = dict(zmin=zmin, zmax=zmax, H=H, neck_z=neck_z, has_head=has_head,
              arm_x=arm_x, arm_top=arm_top, arm_bot=arm_bot,
              leg_x=leg_x, leg_top=leg_top)
    for k in sorted(lm):
        v = lm[k]
        print("  LANDMARK %-10s %s" % (k, ("%8.4f" % v) if isinstance(v, float) else v))
    return lm


def bone_plan(lm):
    """(name, parent, head, tail) in mesh space, ordered parent-first."""
    zmin, zmax, H = lm["zmin"], lm["zmax"], lm["H"]
    neck = lm["neck_z"]
    ax, az0, az1 = lm["arm_x"], lm["arm_top"], lm["arm_bot"]
    lx, lz = lm["leg_x"], lm["leg_top"]

    hips_z = zmin + 0.16 * H
    chest_z = neck - 0.30 * H
    head_top = zmax - 0.10 * H

    head = [
        ("Root",       None,         (0, 0, zmin),             (0, 0, hips_z)),
        ("Hips",       "Root",       (0, 0, hips_z),           (0, 0, chest_z)),
        ("Chest",      "Hips",       (0, 0, chest_z),          (0, 0, neck)),
        ("Head",       "Chest",      (0, 0, neck),             (0, 0, head_top)),
    ] if lm["has_head"] else [
        ("Root",       None,         (0, 0, zmin),             (0, 0, hips_z)),
        ("Hips",       "Root",       (0, 0, hips_z),           (0, 0, chest_z)),
        ("Chest",      "Hips",       (0, 0, chest_z),          (0, 0, zmax)),
        ("Shoulder.L", "Chest",      (0.04, 0, neck - 0.05 * H), (ax, 0, az0)),
        ("Arm.L",      "Shoulder.L", (ax, 0, az0),             (ax, 0, az1 + 0.10 * H)),
        ("Hand.L",     "Arm.L",      (ax, 0, az1 + 0.10 * H),  (ax, 0, az1)),
        ("Shoulder.R", "Chest",      (-0.04, 0, neck - 0.05 * H), (-ax, 0, az0)),
        ("Arm.R",      "Shoulder.R", (-ax, 0, az0),            (-ax, 0, az1 + 0.10 * H)),
        ("Hand.R",     "Arm.R",      (-ax, 0, az1 + 0.10 * H), (-ax, 0, az1)),
        ("Leg.L",      "Hips",       (lx, 0, lz),              (lx, 0, zmin + 0.035 * H)),
        ("Foot.L",     "Leg.L",      (lx, 0, zmin + 0.035 * H), (lx, -0.05, zmin)),
        ("Leg.R",      "Hips",       (-lx, 0, lz),             (-lx, 0, zmin + 0.035 * H)),
        ("Foot.R",     "Leg.R",      (-lx, 0, zmin + 0.035 * H), (-lx, -0.05, zmin)),
    ]
    return head


def classify_piece(centre, lm):
    """Choose one bone for a whole rigid piece, from where its centroid sits.

    Per-vertex voting was tried first and is unreliable: the pieces straddle the
    label boundaries, so votes came out as low as 31% and whole arm chunks landed
    on Hips and flew off with the torso. A piece is rigid, so it gets classified
    once, and the lobes are far enough apart in x for the split to be unambiguous.
    """
    cx, cz = centre[0], centre[2]
    right = cx < 0
    side = ".R" if right else ".L"

    arm_inner = 0.62 * lm["arm_x"]      # arm lobes sit well outside the torso
    rod_inner = 0.30 * lm["arm_x"]      # shoulder rods bridge torso to arm
    arm_len = max(lm["arm_top"] - lm["arm_bot"], 1e-9)

    if lm["has_head"] and cz > lm["neck_z"]:
        return "Head"                    # dome and ears

    if abs(cx) > arm_inner:
        if cz < lm["arm_bot"] + 0.25 * arm_len:
            return "Hand" + side         # claw cluster
        return "Arm" + side

    if abs(cx) > rod_inner and cz > lm["leg_top"]:
        return "Shoulder" + side         # rod swings with the shoulder, not the arm

    if cz < lm["leg_top"]:
        if cz < lm["zmin"] + 0.05 * lm["H"]:
            return "Foot" + side
        return "Leg" + side

    return "Chest"                       # the torso shell is a single rigid piece


def components(mesh):
    """Connected vertex groups of the mesh, largest first."""
    adj = collections.defaultdict(list)
    for e in mesh.data.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)

    seen, comps = set(), []
    for v in range(len(mesh.data.vertices)):
        if v in seen:
            continue
        stack, group = [v], []
        seen.add(v)
        while stack:
            u = stack.pop()
            group.append(u)
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        comps.append(group)
    comps.sort(key=len, reverse=True)
    return comps


def main():
    args = argv_after_dashes()
    if len(args) < 2:
        sys.exit("usage: ... -- <quad.fbx> <out.fbx>")
    src, dst = args[0], args[1]

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=src)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    mesh = meshes[0]
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    remove_base_plate(mesh)

    co = np.array([v.co[:] for v in mesh.data.vertices])
    comps = components(mesh)
    print("LANDMARKS from %d verts, %d pieces:" % (len(co), len(comps)))
    lm = landmarks(co, comps)
    plan = bone_plan(lm)
    bone_names = [n for n, _, _, _ in plan if n != "Root"]

    # --- armature ---
    arm_data = bpy.data.armatures.new("VoxxyArmature")
    arm_obj = bpy.data.objects.new("Voxxy_Armature", arm_data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    for name, parent, head, tail in plan:
        eb = arm_data.edit_bones.new(name)
        eb.head, eb.tail = Vector(head), Vector(tail)
        if parent:
            eb.parent = arm_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")

    # --- binding: whole pieces, rigid ---
    comps = components(mesh)
    assignment = collections.defaultdict(list)
    for group in comps:
        assignment[classify_piece(co[group].mean(axis=0), lm)].extend(group)

    for vg in list(mesh.vertex_groups):
        mesh.vertex_groups.remove(vg)

    print("BINDING (%d pieces, rigid weight 1.0):" % len(comps))
    for name in bone_names:
        idx = assignment.get(name, [])
        vg = mesh.vertex_groups.new(name=name)
        if idx:
            vg.add(idx, 1.0, "REPLACE")
        print("  %-11s %5d verts" % (name, len(idx)))

    mesh.parent = arm_obj
    mod = mesh.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj

    # --- place for Unity: feet at origin, standing TARGET_HEIGHT tall ---
    # Only the armature is transformed. The mesh is its child, so it inherits this;
    # setting the same transform on both applies it twice, which leaves the rest pose
    # looking correct (bones are identity at rest) but makes every posed bone deform
    # in the wrong space and fling its piece off.
    scale = TARGET_HEIGHT / lm["H"]
    arm_obj.location = (0, 0, -lm["zmin"] * scale)
    arm_obj.scale = (scale, scale, scale)
    mesh.location = (0, 0, 0)
    mesh.scale = (1, 1, 1)
    print("TRANSFORM scale=%.4f  height=%.3fm  feet at z=0" % (scale, lm["H"] * scale))

    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
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


if __name__ == "__main__":
    main()
