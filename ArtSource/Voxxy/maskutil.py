"""Separate Voxxy from the model sheet's studio backdrop.

Brightness thresholding does not work here: Voxxy's white bezels and limb bands are
brighter than parts of the backdrop, so any global cutoff that removes the background
also eats them. Instead the background is region-grown inward from the image border
with a per-step tolerance -- the backdrop's gradient is smooth enough to propagate
through, the character's edges are sharp enough to stop it.
"""

import bpy
import numpy as np

EPS = 0.016  # per-step luminance tolerance for the region grow


def load_rgb(path):
    """Load a PNG as a top-down float RGB array."""
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return px[::-1, :, :3]  # Blender stores bottom-up


def subject_mask(rgb, downscale=1, eps=EPS):
    """True where the character is, False for backdrop."""
    lum = rgb.mean(axis=2)[::downscale, ::downscale]
    h, w = lum.shape

    bg = np.zeros((h, w), dtype=bool)
    bg[0, :] = bg[-1, :] = True
    bg[:, 0] = bg[:, -1] = True

    while True:
        grown = bg.copy()
        grown[1:, :] |= bg[:-1, :] & (np.abs(lum[1:, :] - lum[:-1, :]) < eps)
        grown[:-1, :] |= bg[1:, :] & (np.abs(lum[:-1, :] - lum[1:, :]) < eps)
        grown[:, 1:] |= bg[:, :-1] & (np.abs(lum[:, 1:] - lum[:, :-1]) < eps)
        grown[:, :-1] |= bg[:, 1:] & (np.abs(lum[:, :-1] - lum[:, 1:]) < eps)
        if grown.sum() == bg.sum():
            break
        bg = grown

    return ~bg


def fill_holes(mask):
    """Close interior pockets the grow could not reach from outside."""
    outside = np.zeros_like(mask)
    outside[0, :] = outside[-1, :] = True
    outside[:, 0] = outside[:, -1] = True
    outside &= ~mask
    while True:
        grown = outside.copy()
        grown[1:, :] |= outside[:-1, :]
        grown[:-1, :] |= outside[1:, :]
        grown[:, 1:] |= outside[:, :-1]
        grown[:, :-1] |= outside[:, 1:]
        grown &= ~mask
        if grown.sum() == outside.sum():
            break
        outside = grown
    return ~outside


def label_components(mask, downscale=2):
    """Label connected True regions of a boolean mask, largest first.

    Model sheets carry baked-in text (titles, per-view captions) which masks as
    subject just like the character does. Keeping only the largest blob per cell
    drops it without any text-specific heuristics.
    """
    small = mask[::downscale, ::downscale]
    h, w = small.shape
    parent = {}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    labels = np.zeros((h, w), dtype=np.int32)
    nxt = 1
    for y in range(h):
        row = small[y]
        for x in range(w):
            if not row[x]:
                continue
            left = labels[y, x - 1] if x > 0 and small[y, x - 1] else 0
            up = labels[y - 1, x] if y > 0 and small[y - 1, x] else 0
            if left and up:
                labels[y, x] = left
                union(left, up)
            elif left or up:
                labels[y, x] = left or up
            else:
                parent[nxt] = nxt
                labels[y, x] = nxt
                nxt += 1

    for lab in list(parent):
        parent[lab] = find(lab)
    if parent:
        flat = np.zeros(max(parent) + 1, dtype=np.int32)
        for lab, root in parent.items():
            flat[lab] = root
        labels = flat[labels]

    out = []
    for lab in np.unique(labels):
        if lab == 0:
            continue
        ys, xs = np.where(labels == lab)
        out.append(dict(label=int(lab), size=len(ys),
                        x0=int(xs.min()) * downscale, x1=int(xs.max() + 1) * downscale,
                        y0=int(ys.min()) * downscale, y1=int(ys.max() + 1) * downscale))
    out.sort(key=lambda c: -c["size"])
    return out, labels, downscale


def blob_mask(mask, labels, downscale, label):
    """Full-resolution mask of one labelled blob.

    Selecting by bounding box instead would keep anything that merely overlaps the
    box -- a caption behind the character's outline survives that way.
    """
    region = (labels == label)
    grown = np.repeat(np.repeat(region, downscale, axis=0), downscale, axis=1)
    grown = grown[:mask.shape[0], :mask.shape[1]]
    if grown.shape != mask.shape:
        pad = np.zeros(mask.shape, dtype=bool)
        pad[:grown.shape[0], :grown.shape[1]] = grown
        grown = pad
    return mask & grown


def save_rgba(rgb, alpha, path):
    h, w = alpha.shape
    out = np.empty((h, w, 4), dtype=np.float32)
    out[:, :, :3] = rgb
    out[:, :, 3] = alpha
    img = bpy.data.images.new(path.rsplit("/", 1)[-1], width=w, height=h, alpha=True)
    img.alpha_mode = "STRAIGHT"
    img.pixels = out[::-1].ravel().tolist()
    img.file_format = "PNG"
    img.filepath_raw = path
    img.save()
    bpy.data.images.remove(img)
