# AGENT.md — DevoxxGame

Instructions for AI agents working in this repository. Read this before touching code or assets.

## Project

- **Engine:** Unity **6.6** — exact editor version `6000.6.3f1`. Do not upgrade the editor, packages, or API level without being asked.
- **Render pipeline:** Universal Render Pipeline (URP 17.6).
- **Input:** Unity Input System (`com.unity.inputsystem`, 1.20) — the new one. Never use legacy `Input.GetKey` / `Input.GetAxis`.
- **Root namespace:** `DevoxxGame`.
- **Status:** freshly scaffolded. Assets currently hold only the default template content (`Scenes/`, `Settings/`, `TutorialInfo/`, `InputSystem_Actions.inputactions`).

### Core libraries

**None.** No third-party packages, no DI container, no UniTask, no Odin, no external state machine. Only the Unity packages already in `Packages/manifest.json`.

Do not add a dependency (Package Manager, OpenUPM, git URL, or a dropped-in `.dll`) on your own initiative. Propose it, explain what it buys, and wait for approval.

## Tests

There is **no automated test suite** and none is expected. `com.unity.test-framework` ships with the template but is unused — don't write tests unless explicitly asked, and don't claim work is "verified by tests".

Verification instead means: the project compiles without errors or warnings (check the Unity console via MCP), and the reported behaviour is confirmed in the editor — by you through MCP where possible, otherwise by the user following your hand-over steps.

## Code layout & namespaces

- Scripts live under `Assets/Scripts/`.
- **The namespace is `DevoxxGame` + the folder path below `Scripts/`, dot-separated.**
  - `Assets/Scripts/Player/Movement/PlayerMover.cs` → `namespace DevoxxGame.Player.Movement`
  - `Assets/Scripts/Core/GameLoop.cs` → `namespace DevoxxGame.Core`
  - `Assets/Scripts/PlayerConfig.cs` → `namespace DevoxxGame`
- **One class per file**, and the file name matches the type name exactly. This includes enums, interfaces, and structs — each gets its own file. The only exception is a private nested type that is a genuine implementation detail of its owner.
- Folder structure reflects features, not Unity types. Prefer `Scripts/Enemies/Spawning/` over `Scripts/MonoBehaviours/`.
- Editor-only code goes in an `Editor/` folder (e.g. `Assets/Scripts/Editor/`), namespace `DevoxxGame.Editor...`, and must never be referenced from runtime code.

## Serialized fields

Inspector-exposed state uses the auto-property backing-field form, always:

```csharp
[field: SerializeField] public float MoveSpeed { get; private set; }
[field: SerializeField] public Transform SpawnPoint { get; private set; }
```

Rules:
- `public` property, `private set` — writable from the inspector and from the declaring type, read-only to everyone else.
- Never expose a bare `public` field, and never a `[SerializeField] private` field paired with a hand-written `public T Foo => _foo;` wrapper.
- `[field: SerializeReference]` for polymorphic serialized data; `[field: SerializeField]` otherwise.
- Attributes that decorate the serialized field need the `field:` prefix too: `[field: SerializeField, field: Range(0f, 1f)]`.
- Truly internal runtime state that must survive a domain reload but not be authored stays `private` with `[SerializeField]` and no property. Keep this rare.

## Architecture

### Data driven — data lives in ScriptableObjects

- **Tunable values, content, and configuration belong in `ScriptableObject` assets**, not hard-coded in `MonoBehaviour`s and not in scene-instance inspector overrides.
- A `MonoBehaviour` holds a reference to its config SO and reads from it. It does not own the numbers.
- Config SOs are immutable at runtime: expose data via `{ get; private set; }` and never write to an SO during play (it persists in the editor and silently corrupts authored data).
- Mutable runtime state lives in plain C# classes or component instances, not in SO assets.
- Give every SO a `[CreateAssetMenu(menuName = "DevoxxGame/...")]` so it is authorable.
- SO assets live under `Assets/Data/<Feature>/`.

### SOLID

Apply it concretely, not as decoration:
- **S** — a component does one job. An input reader reads input; it does not also move, animate, and play audio.
- **O** — extend by adding a new SO variant or a new implementation of an interface, not by growing an `if`/`switch` over type enums.
- **L** — a subclass must be safely usable through its base type; don't override a method into a no-op.
- **I** — small, purpose-shaped interfaces (`IDamageable`, `IInteractable`) over one fat `IEntity`.
- **D** — depend on interfaces and data, not on concrete singletons. Wire the concrete type at the composition point (a prefab root, a bootstrapper component).

Keep it proportional: this is a game project, not an enterprise layer cake. Don't add an interface with exactly one implementation and no plausible second one just to satisfy a letter.

## Wiring references

**Never hook up references across scene objects in the scene.** Dragging a reference from one scene object to an unrelated one is not allowed — it is invisible in diffs, breaks on scene merges, and silently nulls out.

Allowed:
- **References within the same prefab** — a child `Transform`, a sibling component, a nested renderer, all assigned in the prefab. This is the preferred way to wire.
- **Asset references** — ScriptableObjects, prefabs, materials, input action assets — assigned on a prefab or on a config SO.
- `GetComponent` / `GetComponentInChildren` / `GetComponentInParent` inside the prefab's own hierarchy, resolved in `Awake`.
- Explicit registration: an object calls a registry/service it was given a reference to, or a bootstrapper injects dependencies it holds as asset references.

### Never use Find-style lookups

Banned outright in runtime code:

- `FindObjectsByType` / `FindFirstObjectByType` / `FindAnyObjectByType`
- `FindObjectOfType` / `FindObjectsOfType` (obsolete)
- `GameObject.Find`, `GameObject.FindWithTag`, `GameObject.FindGameObjectsWithTag`
- `Transform.Find` and path-string lookups (`transform.Find("Root/Arm/Hand")`)
- `Object.FindObjectsOfTypeAll`, `Resources.FindObjectsOfTypeAll`
- `Resources.Load` by magic path string
- `Camera.main` (it is a tagged find) — take the camera as a reference instead
- `SendMessage` / `BroadcastMessage`

If you reach for one of these, the dependency structure is wrong. Fix it with a prefab reference, an SO reference, a registry the object is handed, or an event. Editor-only tooling under an `Editor/` folder may use `Find*` where there is no alternative.

## General practices

- No `MonoBehaviour` singletons with `static Instance` as a default habit. If global access is genuinely needed, use an SO-based service the consumers reference as an asset.
- `Awake` for self-wiring (own hierarchy, own components), `OnEnable`/`OnDisable` for subscribing and unsubscribing — every subscription gets a matching unsubscription.
- Keep `Update` lean: no allocations, no `GetComponent`, no LINQ in per-frame paths. Cache in `Awake`.
- Prefer `[SerializeField]`-authored data and composition over inheritance chains of `MonoBehaviour`s.
- Nullable-unfriendly Unity objects: check destroyed references with `if (obj)`, not `!= null` where it matters.
- Match the style of surrounding code. No comment noise — comment *why*, never *what*.
- `.meta` files are part of the source. Never delete or hand-edit one; never move or rename an asset outside Unity or the MCP tools, or the GUID link breaks.
- Do not edit `.unity` scene files, `.prefab` files, or `ProjectSettings/*` by hand as text. Use Unity via MCP.

## Working with Unity — use MCP

**Use the Unity MCP tools wherever they can do the job.** That includes:
- reading the console for compile errors and runtime logs after every change that touches code,
- running editor commands, creating and configuring assets, inspecting the scene,
- capturing the scene view or camera to actually look at the result rather than assuming it.

Writing a `.cs` file with Bash/Write is fine — but after writing, ask Unity to recompile and **read the console** before reporting anything as done. "It should work" is not a report.

### Hand-over for in-editor wiring

When something genuinely cannot be done through MCP (a manual inspector assignment, an import setting, a platform toggle, a scene authoring step), hand it over explicitly. Never leave it implied, and never pretend it is finished.

Format the hand-over as numbered, literal steps:

1. Say up front what is not wired yet and what will be broken until it is.
2. One action per step, naming the exact asset path, GameObject, component, and field — e.g. *"Open `Assets/Scenes/SampleScene.unity`, select `Player`, and in the `PlayerMover` component set **Config** to `Assets/Data/Player/DefaultPlayerConfig.asset`."*
3. Give the expected end state, so the user can tell it worked.
4. State how to verify — what to press, what should happen.
5. Ask them to confirm; then re-check the console via MCP before continuing.

Keep the steps short enough to follow without re-reading, and don't bundle three assignments into one bullet.
