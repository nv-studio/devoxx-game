"""Split the Voxxy model sheet into one PNG per view.

Run headless:
    blender --background --python ArtSource/Voxxy/prep_reference.py

The sheet is a 5x2 grid on a light-grey studio backdrop. The backdrop is kept rather
than keyed out: Voxxy's own white panels sit within a few percent of the backdrop
value, so any threshold that removes the background also eats the bezels. The build
renders onto this same colour instead, which makes the comparison sheets exact.
"""

import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SHEET = os.path.normpath(os.path.join(HERE, "..", "..", "Assets", "Art", "voxxy-robot.png"))
OUT = os.path.join(HERE, "ref")

COLS = 5
ROWS = 2
# Measured from the sheet: the only gap with no subject pixels is the row split at y=786.
ROW_BOUNDS = [(0, 784), (790, 1536)]


def load_rgb(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return px[::-1]  # Blender stores bottom-up; flip to top-down


def save_rgba(arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=True)
    img.pixels = arr[::-1].ravel().tolist()
    img.file_format = "PNG"
    img.filepath_raw = path
    img.save()
    bpy.data.images.remove(img)


def main():
    if not os.path.exists(SHEET):
        sys.exit("sheet not found: %s" % SHEET)
    os.makedirs(OUT, exist_ok=True)

    sheet = load_rgb(SHEET)
    h, w = sheet.shape[:2]
    print("sheet %dx%d" % (w, h))

    # Backdrop colour, sampled from a corner well clear of any subject.
    bg = sheet[20:60, 20:60, :3].reshape(-1, 3).mean(axis=0)
    print("backdrop rgb %.4f %.4f %.4f  (hex #%02X%02X%02X)" % (
        bg[0], bg[1], bg[2], *[int(round(c ** (1 / 2.2) * 255)) for c in bg]))

    edges = [round(i * w / COLS) for i in range(COLS + 1)]
    index = 0
    for r, (y0, y1) in enumerate(ROW_BOUNDS):
        for c in range(COLS):
            x0, x1 = edges[c], edges[c + 1]
            cell = sheet[y0:y1, x0:x1]
            path = os.path.join(OUT, "%02d.png" % index)
            save_rgba(cell, path)

            # Report the subject's bounding box so the build can match framing.
            dark = cell[:, :, :3].min(axis=2) < 0.80
            ys, xs = np.where(dark)
            if len(ys):
                print("%02d  cell x=%d..%d y=%d..%d  subject x=%d..%d y=%d..%d  h=%d" % (
                    index, x0, x1, y0, y1,
                    xs.min(), xs.max(), ys.min(), ys.max(), ys.max() - ys.min()))
            else:
                print("%02d  cell x=%d..%d y=%d..%d  (no subject found)" % (index, x0, x1, y0, y1))
            index += 1

    print("wrote %d views to %s" % (index, OUT))


main()
