# Generation log

Provenance for the three characters in `Assets/Art/`. Each `.json` here is the sidecar the
Unity AI Toolkit wrote next to a generated mesh, recording the model used, the prompt, and
the reference images fed in. The Toolkit's cache (`GeneratedAssets/`) was removed once the
characters were final; these sidecars are kept because the prompts are the recipe for
regenerating a character, and they are easier to find here than in git history.

The original cache, meshes included, is in history at commit `b467ede`.

## Runs

| Sidecar | Model | Produced | Where that mesh is now |
| --- | --- | --- | --- |
| `voxxy-p1-manual-01.json` | `model3d-tripo-p1` | Voxxy, 1st attempt | gone — superseded |
| `voxxy-p1-manual-02.json` | `model3d-tripo-p1` | Voxxy, 2nd attempt | gone — was `Assets/New Mesh.fbx` |
| `voxxy-p1-manual-glb.json` | `model3d-tripo-p1` | Voxxy, `.glb` | gone — was `Assets/model.glb` |
| `voxxy-multiview-quad.json` | `model3d-tripo-p2-multiview-quad` | Voxxy quad mesh | `ArtSource/Voxxy/Voxxy_quad.fbx` |
| `voxxy-rigging-v1.json` | `model3d-tripo-rigging-v1` | Voxxy auto-rig (rejected) | `ArtSource/Voxxy/Voxxy_rigged_auto.fbx` |
| `droid-multiview-quad.json` | `model3d-tripo-p2-multiview-quad` | Droid quad mesh | `ArtSource/Droid/Droid_quad.fbx` |
| `droid-rigging-v1.json` | `model3d-tripo-rigging-v1` | Droid auto-rig (**kept** — Humanoid) | `ArtSource/Droid/Droid_rigged.fbx` |
| `biggy-multiview-quad-v1.json` | `model3d-tripo-p2-multiview-quad` | Biggy, 1st attempt | gone — see below |
| `biggy-multiview-quad-v2.json` | `model3d-tripo-p2-multiview-quad` | Biggy quad mesh | `ArtSource/Biggy/Biggy_quad.fbx` |

The three `*_quad.fbx` files are byte-identical to the cache originals (SHA-1 verified before
deletion). The two `*_rigged*.fbx` are Blender 5.1.2 re-exports of the Tripo output with
textures embedded — same rig, different bytes.

## The three manual runs were the wrong shape of request

`voxxy-p1-manual-*` set `promptImageReferenceGuid` — a single image — so Tripo was handed one
picture containing ten small robots rather than one character from several angles. The
multiview runs set `multiviewFrontGuid` / `BackGuid` / `LeftGuid` / `RightGuid` instead, which
is what produced usable geometry. If you regenerate, use the multiview form.

`voxxy-p1-manual-glb` is the run whose output carried a stray 20x20 debug grid beside the
character.

## Biggy v1 vs v2

Both were fed the same three views. v1 came back with the orange belly on the **front and the
back**, because the prompt did not say the belly was front-only. v2's prompt adds "on the
FRONT only ... The BACK is plain dark blue-grey armour", and that is the mesh that shipped.

Related: the Biggy model sheet's own captions are wrong. The cell captioned "BACK VIEW" is
another front view; the real back view is the cell captioned "BACK-LEFT".

## Sheet cell -> generator slot

The generator inputs were cut from the model sheets in `Assets/Art/*-robot.png`, split into
cells by `ArtSource/Voxxy/sheet_split.py` (output in `ArtSource/<Char>/ref/NN.png`), then given
a real alpha channel by `cut_reference.py` because the generators reject an opaque backdrop.

Voxxy's mapping is recorded in `cut_reference.py`:

    00 -> front    06 -> back    07 -> left    05 -> right

**Droid's and Biggy's mappings are not recorded anywhere.** `cut_reference.py` was only ever
parameterised for Voxxy; the other two were cut ad hoc. All that is known for certain is
Biggy's back view, which is the cell captioned "BACK-LEFT" per the note above. If those
cut-outs are needed again, the mapping has to be re-derived by eye from the sheets — or
recovered from the set-aside copies of `Assets/Art/Reference/*.png`, which were removed from
the project before commit `b467ede` and so are not in git history.

Generalising `cut_reference.py` to take a character name and carry a per-character `VIEWS`
map would close that gap.
