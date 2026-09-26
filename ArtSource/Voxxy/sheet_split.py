"""Split a character model sheet into per-view PNGs with transparent backgrounds.

Unity AI Toolkit's mesh generators reject references that still have a background,
and the sheets carry baked-in captions that must not reach the generator either.
Each cell is masked independently (its own border is background), then only the
largest blob in the cell is kept opaque, which drops titles and captions.

Run headless:
    blender --background --python ArtSource/Voxxy/sheet_split.py -- <sheet.png> <cols> <rows> <out_dir>
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import maskutil  # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) < 4:
        sys.exit("usage: ... -- <sheet.png> <cols> <rows> <out_dir>")
    sheet_path, cols, rows, out_dir = args[0], int(args[1]), int(args[2]), args[3]

    os.makedirs(out_dir, exist_ok=True)
    sheet = maskutil.load_rgb(sheet_path)
    h, w = sheet.shape[:2]
    print("SHEET %s  %dx%d  grid %dx%d" % (os.path.basename(sheet_path), w, h, cols, rows))

    xe = [round(i * w / cols) for i in range(cols + 1)]
    ye = [round(j * h / rows) for j in range(rows + 1)]

    index = 0
    for r in range(rows):
        for c in range(cols):
            cell = sheet[ye[r]:ye[r + 1], xe[c]:xe[c + 1]]
            mask = maskutil.fill_holes(maskutil.subject_mask(cell))

            blobs, labels, ds = maskutil.label_components(mask)
            if not blobs:
                print("%02d  (empty cell)" % index)
                index += 1
                continue

            # Keep only the largest blob: the character, never a caption.
            b = blobs[0]
            keep = maskutil.blob_mask(mask, labels, ds, b["label"])

            path = os.path.join(out_dir, "%02d.png" % index)
            maskutil.save_rgba(cell, keep.astype(np.float32), path)

            ch, cw = mask.shape
            print("%02d  cell %dx%d  subject %5.1f%%  bbox x=%d..%d y=%d..%d  dropped %d blob(s)" % (
                index, cw, ch, 100.0 * keep.sum() / keep.size,
                b["x0"], b["x1"], b["y0"], b["y1"], len(blobs) - 1))
            index += 1

    print("WROTE %d views to %s" % (index, out_dir))


main()
