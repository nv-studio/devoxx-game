"""Write background-free versions of the four generator input views.

Unity AI Toolkit's mesh generators reject references that still have a background,
so the crops from prep_reference.py get a real alpha channel here.

Run headless:
    blender --background --python ArtSource/Voxxy/cut_reference.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import maskutil  # noqa: E402

REF = os.path.join(HERE, "ref")
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "Assets", "Art", "Reference"))

# source crop -> generator slot
VIEWS = {
    "00": "front",
    "06": "back",
    "07": "left",   # visor points image-left: we see the character's left side
    "05": "right",
}


def main():
    os.makedirs(OUT, exist_ok=True)

    for idx, slot in sorted(VIEWS.items(), key=lambda kv: kv[1]):
        src = os.path.join(REF, "%s.png" % idx)
        rgb = maskutil.load_rgb(src)

        mask = maskutil.fill_holes(maskutil.subject_mask(rgb))
        alpha = mask.astype(np.float32)

        dst = os.path.join(OUT, "voxxy_%s.png" % slot)
        maskutil.save_rgba(rgb, alpha, dst)

        ys, xs = np.where(mask)
        h, w = mask.shape
        print("%-6s %s -> %s  %dx%d  subject %.1f%% of frame  bbox x=%d..%d y=%d..%d" % (
            slot, idx, os.path.basename(dst), w, h,
            100.0 * mask.sum() / mask.size,
            xs.min(), xs.max(), ys.min(), ys.max()))


main()
