"""Tile the alpha channels of a ref folder so the cutouts can be inspected directly.

Image viewers composite RGB over white and ignore alpha, so a bad cutout looks
identical to a good one. This renders the mask itself: white = kept, dark = cut.

Run headless:
    blender --background --python ArtSource/Voxxy/alpha_contact.py -- <ref_dir> <cols> <out.png>
"""

import glob
import os
import sys

import bpy
import numpy as np

TILE = (300, 300)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) < 3:
        sys.exit("usage: ... -- <ref_dir> <cols> <out.png>")
    ref_dir, cols, out_path = args[0], int(args[1]), args[2]

    paths = sorted(glob.glob(os.path.join(ref_dir, "*.png")))
    if not paths:
        sys.exit("no PNGs in " + ref_dir)

    tiles = []
    for p in paths:
        img = bpy.data.images.load(p)
        w, h = img.size
        a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, 3]
        bpy.data.images.remove(img)

        tw, th = TILE
        yi = np.clip((np.arange(th) * h / th).astype(int), 0, h - 1)
        xi = np.clip((np.arange(tw) * w / tw).astype(int), 0, w - 1)
        small = a[yi][:, xi]

        rgb = np.zeros((th, tw, 3), dtype=np.float32)
        rgb[:, :, :] = small[:, :, None]          # white subject on black
        rgb[0, :] = rgb[-1, :] = (0.2, 0.4, 0.9)  # tile border
        rgb[:, 0] = rgb[:, -1] = (0.2, 0.4, 0.9)
        tiles.append(rgb)
        print("%-40s alpha opaque %5.1f%%" % (os.path.basename(p), 100.0 * (a > 0.5).mean()))

    rows = (len(tiles) + cols - 1) // cols
    th, tw = TILE[1], TILE[0]
    sheet = np.zeros((rows * th, cols * tw, 3), dtype=np.float32)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = t

    out = np.ones(sheet.shape[:2] + (4,), dtype=np.float32)
    out[:, :, :3] = sheet
    img = bpy.data.images.new("contact", width=sheet.shape[1], height=sheet.shape[0], alpha=True)
    img.pixels = out[::-1].ravel().tolist()
    img.file_format = "PNG"
    img.filepath_raw = out_path
    img.save()
    print("WROTE %s" % out_path)


main()
