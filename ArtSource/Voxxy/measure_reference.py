"""Measure Voxxy's silhouette from the front and side reference views.

Run headless:
    blender --background --python ArtSource/Voxxy/measure_reference.py

Prints a normalised silhouette profile (width at each slice of the subject's height)
for the front and side views, which is what params.json is authored from.

The backdrop can't be separated by brightness alone -- Voxxy's white bezels are
brighter than parts of the backdrop. Instead the background is region-grown from the
border with a per-step smoothness tolerance: the backdrop's gradient is smooth enough
to propagate through, the subject's edges are sharp enough to stop it.
"""

import json
import os

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref")

# view index -> (label, rows of the cell to ignore, e.g. the sheet's title text)
VIEWS = {
    0: ("front", 0),
    1: ("front-3q-l", 0),
    2: ("side-titled", 90),
    3: ("back-3q-r", 0),
    4: ("front-3q-r", 0),
    5: ("side", 0),
    6: ("back", 0),
    7: ("side-r", 0),
    8: ("front-3q", 0),
    9: ("low-angle", 0),
}

# the views worth printing a full silhouette profile for
PROFILED = (0, 2, 5, 6)

EPS = 0.016  # per-step luminance tolerance for the background region grow
DOWNSCALE = 2


def load(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    return px


def subject_mask(rgb):
    lum = rgb.mean(axis=2)[::DOWNSCALE, ::DOWNSCALE]
    h, w = lum.shape

    bg = np.zeros((h, w), dtype=bool)
    bg[0, :] = bg[-1, :] = True
    bg[:, 0] = bg[:, -1] = True

    while True:
        grown = bg.copy()
        # propagate into each of the four neighbours where the step is smooth
        grown[1:, :] |= bg[:-1, :] & (np.abs(lum[1:, :] - lum[:-1, :]) < EPS)
        grown[:-1, :] |= bg[1:, :] & (np.abs(lum[:-1, :] - lum[1:, :]) < EPS)
        grown[:, 1:] |= bg[:, :-1] & (np.abs(lum[:, 1:] - lum[:, :-1]) < EPS)
        grown[:, :-1] |= bg[:, 1:] & (np.abs(lum[:, :-1] - lum[:, 1:]) < EPS)
        if grown.sum() == bg.sum():
            break
        bg = grown

    return ~bg


def report(name, mask, skip_rows, profile=True):
    mask = mask.copy()
    if skip_rows:
        mask[: skip_rows // DOWNSCALE] = False

    ys, xs = np.where(mask)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    height = y1 - y0 + 1
    cx = (x0 + x1) / 2.0

    bbox = {
        "x0": x0 * DOWNSCALE, "x1": (x1 + 1) * DOWNSCALE,
        "y0": y0 * DOWNSCALE, "y1": (y1 + 1) * DOWNSCALE,
    }

    if not profile:
        print("%-14s bbox w=%4d h=%4d" % (name, (x1 - x0 + 1) * DOWNSCALE, height * DOWNSCALE))
        return bbox

    print("\n=== %s ===" % name)
    print("bbox w=%d h=%d   aspect(w/h)=%.3f" % (x1 - x0 + 1, height, (x1 - x0 + 1) / height))
    print(" t      width   left    right    (fractions of subject height, from the top)")

    for i in range(41):
        t = i / 40.0
        y = int(round(y0 + t * (height - 1)))
        row = np.where(mask[y])[0]
        if len(row) == 0:
            print("%5.3f    --" % t)
            continue
        print("%5.3f  %6.3f  %+6.3f  %+6.3f" % (
            t,
            (row.max() - row.min() + 1) / height,
            (row.min() - cx) / height,
            (row.max() - cx) / height,
        ))
    return bbox


def main():
    boxes = {}
    for idx, (label, skip) in sorted(VIEWS.items()):
        path = os.path.join(REF, "%02d.png" % idx)
        mask = subject_mask(load(path))
        boxes["%02d" % idx] = dict(
            report("%s (%02d)" % (label, idx), mask, skip, profile=idx in PROFILED),
            label=label,
        )

    out = os.path.join(REF, "bboxes.json")
    with open(out, "w") as fh:
        json.dump(boxes, fh, indent=2, sort_keys=True)
    print("\nwrote %s" % out)


main()
