using System;
using DevoxxGame.Characters;
using DevoxxGame.Characters.Configuration;
using DevoxxGame.Players;
using Unity.Cinemachine;
using Unity.Cinemachine.TargetTracking;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

namespace DevoxxGame.Editor
{
    /// <summary>
    /// Builds the gameplay prototype assets from scratch: layers, placeholder materials, the avatar
    /// and character prefabs, the player rig, the config assets and the Testing scene.
    ///
    /// Everything it produces is authored through Unity's own APIs, so running it twice simply
    /// rebuilds the same assets rather than accumulating duplicates.
    /// </summary>
    public static class GameplayBootstrapper
    {
        const string InputActionsPath = "Assets/InputSystem_Actions.inputactions";
        const string TestingScenePath = "Assets/Scenes/Testing.unity";

        const string AvatarPrefabPath = "Assets/Prefabs/Characters/Avatars/CylinderAvatar.prefab";
        const string CharacterPrefabPath = "Assets/Prefabs/Characters/Character.prefab";
        const string PlayerRigPrefabPath = "Assets/Prefabs/Players/PlayerRig.prefab";

        const string AvatarMaterialPath = "Assets/Prefabs/Characters/Avatars/PlaceholderAvatar.mat";
        const string GroundMaterialPath = "Assets/Prefabs/Characters/Avatars/PlaceholderGround.mat";

        const string MovementConfigPath = "Assets/Data/Characters/DefaultMovement.asset";
        const string AvatarConfigPath = "Assets/Data/Characters/Avatars/CylinderAvatar.asset";
        const string CharacterConfigPath = "Assets/Data/Characters/TestCharacter.asset";

        [MenuItem("DevoxxGame/Bootstrap Gameplay Prototype")]
        public static void Run()
        {
            var groundLayer = EnsureLayer("Ground");
            var characterLayer = EnsureLayer("Character");

            var avatarMaterial = EnsureMaterial(AvatarMaterialPath, new Color(0.25f, 0.55f, 0.95f));
            var groundMaterial = EnsureMaterial(GroundMaterialPath, new Color(0.32f, 0.34f, 0.38f));

            var avatarPrefab = BuildAvatarPrefab(avatarMaterial);
            var movement = BuildMovementConfig(groundLayer);
            var avatarConfig = BuildAvatarConfig(avatarPrefab);
            var characterConfig = BuildCharacterConfig(avatarConfig, movement);
            var characterPrefab = BuildCharacterPrefab(characterLayer);
            var rigPrefab = BuildPlayerRigPrefab(characterPrefab, characterConfig);

            BuildTestingScene(rigPrefab, groundMaterial, groundLayer);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[GameplayBootstrapper] Done. Open " + TestingScenePath + " and press Play.");
        }

        // ---------------------------------------------------------------- layers

        static int EnsureLayer(string layerName)
        {
            var existing = LayerMask.NameToLayer(layerName);
            if (existing >= 0)
                return existing;

            var tagManagerAssets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset");
            if (tagManagerAssets == null || tagManagerAssets.Length == 0)
                throw new Exception("Could not load ProjectSettings/TagManager.asset");

            var tagManagerAsset = tagManagerAssets[0];

            var tagManager = new SerializedObject(tagManagerAsset);
            var layers = tagManager.FindProperty("layers");

            for (var i = 8; i < layers.arraySize; i++)
            {
                var slot = layers.GetArrayElementAtIndex(i);
                if (!string.IsNullOrEmpty(slot.stringValue))
                    continue;

                slot.stringValue = layerName;
                tagManager.ApplyModifiedPropertiesWithoutUndo();
                AssetDatabase.SaveAssets();
                Debug.Log($"[GameplayBootstrapper] Created layer '{layerName}' at index {i}.");
                return i;
            }

            throw new Exception($"No free user layer slot available for '{layerName}'.");
        }

        // ---------------------------------------------------------------- assets

        static Material EnsureMaterial(string path, Color color)
        {
            var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (existing)
                return existing;

            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (!shader)
                throw new Exception("URP Lit shader not found - is URP the active pipeline?");

            var material = new Material(shader) { name = System.IO.Path.GetFileNameWithoutExtension(path) };
            material.SetColor("_BaseColor", color);

            EnsureFolder(path);
            AssetDatabase.CreateAsset(material, path);
            return material;
        }

        static T EnsureAsset<T>(string path) where T : ScriptableObject
        {
            var existing = AssetDatabase.LoadAssetAtPath<T>(path);
            if (existing)
                return existing;

            var asset = ScriptableObject.CreateInstance<T>();
            EnsureFolder(path);
            AssetDatabase.CreateAsset(asset, path);
            return asset;
        }

        static void EnsureFolder(string assetPath)
        {
            var folder = System.IO.Path.GetDirectoryName(assetPath)?.Replace('\\', '/');
            if (string.IsNullOrEmpty(folder) || AssetDatabase.IsValidFolder(folder))
                return;

            var parts = folder.Split('/');
            var current = parts[0];
            for (var i = 1; i < parts.Length; i++)
            {
                var next = current + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, parts[i]);
                current = next;
            }
        }

        // ---------------------------------------------------------------- configs

        static MovementConfig BuildMovementConfig(int groundLayer)
        {
            var config = EnsureAsset<MovementConfig>(MovementConfigPath);
            using (var edit = new Fields(config))
            {
                edit.Str("DisplayName", "Default Movement")
                    .Num("MaxSpeed", 6f)
                    .Num("Acceleration", 40f)
                    .Num("Deceleration", 60f)
                    .Num("TurnSpeed", 720f)
                    .Num("AirAccelerationMultiplier", 0.4f)
                    .Num("JumpHeight", 1.5f)
                    .Num("FallGravityMultiplier", 2f)
                    .Num("CoyoteTime", 0.12f)
                    .Num("JumpBufferTime", 0.12f)
                    .Num("GroundProbeRadius", 0.4f)
                    .Num("GroundProbeDistance", 0.25f)
                    .Num("MaxSlopeAngle", 50f)
                    .Int("GroundLayers", 1 << groundLayer);
            }
            EditorUtility.SetDirty(config);
            return config;
        }

        static AvatarConfig BuildAvatarConfig(GameObject modelPrefab)
        {
            var config = EnsureAsset<AvatarConfig>(AvatarConfigPath);
            using (var edit = new Fields(config))
            {
                edit.Str("DisplayName", "Cylinder Avatar")
                    .Ref("ModelPrefab", modelPrefab)
                    .Vec("ModelLocalPosition", Vector3.zero)
                    .Num("ModelScale", 1f)
                    .Num("ColliderHeight", 2f)
                    .Num("ColliderRadius", 0.5f)
                    .Num("CameraTargetHeight", 1.5f);
            }
            EditorUtility.SetDirty(config);
            return config;
        }

        static CharacterConfig BuildCharacterConfig(AvatarConfig avatar, MovementConfig movement)
        {
            var config = EnsureAsset<CharacterConfig>(CharacterConfigPath);
            using (var edit = new Fields(config))
            {
                edit.Str("DisplayName", "Test Character")
                    .Ref("Avatar", avatar)
                    .Ref("Movement", movement);
            }
            EditorUtility.SetDirty(config);
            return config;
        }

        // ---------------------------------------------------------------- prefabs

        static GameObject BuildAvatarPrefab(Material material)
        {
            var cylinder = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            try
            {
                cylinder.name = "CylinderAvatar";
                UnityEngine.Object.DestroyImmediate(cylinder.GetComponent<Collider>());
                cylinder.GetComponent<MeshRenderer>().sharedMaterial = material;

                EnsureFolder(AvatarPrefabPath);
                return PrefabUtility.SaveAsPrefabAsset(cylinder, AvatarPrefabPath);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(cylinder);
            }
        }

        static Character BuildCharacterPrefab(int characterLayer)
        {
            var root = new GameObject("Character");
            try
            {
                var body = root.AddComponent<Rigidbody>();
                body.interpolation = RigidbodyInterpolation.Interpolate;
                body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
                body.constraints = RigidbodyConstraints.FreezeRotationX | RigidbodyConstraints.FreezeRotationZ;

                var collider = root.AddComponent<CapsuleCollider>();
                collider.height = 2f;
                collider.radius = 0.5f;
                collider.center = new Vector3(0f, 1f, 0f);

                var probe = root.AddComponent<GroundProbe>();
                var motor = root.AddComponent<CharacterMotor>();
                var character = root.AddComponent<Character>();

                var visualsObject = new GameObject("Visuals");
                visualsObject.transform.SetParent(root.transform, false);
                var visuals = visualsObject.AddComponent<CharacterVisuals>();

                var cameraTarget = new GameObject("CameraTarget");
                cameraTarget.transform.SetParent(root.transform, false);
                cameraTarget.transform.localPosition = new Vector3(0f, 1.5f, 0f);

                SetLayerRecursively(root, characterLayer);

                using (var edit = new Fields(probe))
                    edit.Ref("Origin", root.transform);

                using (var edit = new Fields(motor))
                    edit.Ref("Body", body).Ref("GroundProbe", probe);

                using (var edit = new Fields(character))
                {
                    edit.Ref("Motor", motor)
                        .Ref("Visuals", visuals)
                        .Ref("Body", collider)
                        .Ref("CameraTarget", cameraTarget.transform);
                }

                EnsureFolder(CharacterPrefabPath);
                var prefab = PrefabUtility.SaveAsPrefabAsset(root, CharacterPrefabPath);
                return prefab.GetComponent<Character>();
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        static GameObject BuildPlayerRigPrefab(Character characterPrefab, CharacterConfig config)
        {
            var root = new GameObject("PlayerRig");
            try
            {
                var cameraObject = new GameObject("PlayerCamera");
                cameraObject.transform.SetParent(root.transform, false);
                cameraObject.tag = "MainCamera";
                var camera = cameraObject.AddComponent<Camera>();
                cameraObject.AddComponent<CinemachineBrain>();
                cameraObject.AddComponent<AudioListener>();

                var vcamObject = new GameObject("ThirdPersonCamera");
                vcamObject.transform.SetParent(root.transform, false);
                var vcam = vcamObject.AddComponent<CinemachineCamera>();

                var orbital = vcamObject.AddComponent<CinemachineOrbitalFollow>();
                orbital.OrbitStyle = CinemachineOrbitalFollow.OrbitStyles.Sphere;
                orbital.Radius = 6f;
                orbital.TrackerSettings.BindingMode = BindingMode.WorldSpace;
                orbital.VerticalAxis.Value = 15f;

                vcamObject.AddComponent<CinemachineRotationComposer>();

                var axisController = vcamObject.AddComponent<CinemachineInputAxisController>();
                axisController.SynchronizeControllers();
                ApplyLookInput(axisController);

                var playerInput = root.AddComponent<PlayerInput>();
                using (var edit = new Raw(playerInput))
                {
                    edit.Ref("m_Actions", AssetDatabase.LoadAssetAtPath<InputActionAsset>(InputActionsPath))
                        .Str("m_DefaultActionMap", "Player")
                        .Int("m_NotificationBehavior", (int)PlayerNotifications.InvokeCSharpEvents)
                        .Ref("m_Camera", camera);
                }

                var reader = root.AddComponent<PlayerInputReader>();
                var cameraRig = root.AddComponent<PlayerCameraRig>();
                var spawner = root.AddComponent<CharacterSpawner>();
                var brain = root.AddComponent<PlayerBrain>();

                using (var edit = new Fields(reader))
                    edit.Ref("Source", playerInput);

                using (var edit = new Fields(cameraRig))
                    edit.Ref("VirtualCamera", vcam).Ref("YawReference", cameraObject.transform);

                using (var edit = new Fields(spawner))
                    edit.Ref("CharacterPrefab", characterPrefab).Ref("Config", config);

                using (var edit = new Fields(brain))
                    edit.Ref("InputReader", reader).Ref("CameraRig", cameraRig).Ref("Spawner", spawner);

                EnsureFolder(PlayerRigPrefabPath);
                return PrefabUtility.SaveAsPrefabAsset(root, PlayerRigPrefabPath);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        static void ApplyLookInput(CinemachineInputAxisController axisController)
        {
            var look = FindActionReference("Player", "Look");
            if (!look)
            {
                Debug.LogWarning("[GameplayBootstrapper] Could not find the Player/Look action reference; " +
                                 "camera look must be assigned by hand.");
                return;
            }

            foreach (var controller in axisController.Controllers)
            {
                switch (controller.Name)
                {
                    case "Look Orbit X":
                        controller.Input.InputAction = look;
                        controller.Input.Gain = 0.3f;
                        controller.Enabled = true;
                        break;
                    case "Look Orbit Y":
                        controller.Input.InputAction = look;
                        controller.Input.Gain = -0.15f;
                        controller.Enabled = true;
                        break;
                    default:
                        // Orbit Scale shares the Look action otherwise, which would zoom while aiming.
                        controller.Enabled = false;
                        break;
                }
            }
        }

        static InputActionReference FindActionReference(string mapName, string actionName)
        {
            foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(InputActionsPath))
            {
                if (asset is not InputActionReference reference || reference.action == null)
                    continue;

                if (reference.action.name == actionName && reference.action.actionMap?.name == mapName)
                    return reference;
            }

            return null;
        }

        // ---------------------------------------------------------------- scene

        static void BuildTestingScene(GameObject rigPrefab, Material groundMaterial, int groundLayer)
        {
            var scene = EditorSceneManager.OpenScene(TestingScenePath, OpenSceneMode.Single);

            foreach (var root in scene.GetRootGameObjects())
            {
                if (root.name is "Main Camera" or "Floor" or "Global Volume" or "PlayerRig" or "Obstacles")
                    UnityEngine.Object.DestroyImmediate(root);
            }

            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Floor";
            floor.transform.localScale = new Vector3(30f, 1f, 30f);
            floor.transform.position = new Vector3(0f, -0.5f, 0f);
            floor.layer = groundLayer;
            floor.GetComponent<MeshRenderer>().sharedMaterial = groundMaterial;

            var obstacles = new GameObject("Obstacles");
            CreateObstacle(obstacles.transform, new Vector3(5f, 0.5f, 3f), new Vector3(2f, 1f, 2f), groundMaterial, groundLayer);
            CreateObstacle(obstacles.transform, new Vector3(-4f, 0.25f, 6f), new Vector3(4f, 0.5f, 2f), groundMaterial, groundLayer);
            CreateObstacle(obstacles.transform, new Vector3(0f, 1.5f, -7f), new Vector3(3f, 3f, 1f), groundMaterial, groundLayer);

            var volumeObject = new GameObject("Global Volume");
            var volume = volumeObject.AddComponent<Volume>();
            volume.isGlobal = true;
            volume.sharedProfile = AssetDatabase.LoadAssetAtPath<VolumeProfile>("Assets/Settings/SampleSceneProfile.asset");

            var rig = (GameObject)PrefabUtility.InstantiatePrefab(rigPrefab, scene);
            rig.transform.position = Vector3.zero;

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
        }

        static void CreateObstacle(Transform parent, Vector3 position, Vector3 scale, Material material, int layer)
        {
            var obstacle = GameObject.CreatePrimitive(PrimitiveType.Cube);
            obstacle.name = "Obstacle";
            obstacle.transform.SetParent(parent, false);
            obstacle.transform.position = position;
            obstacle.transform.localScale = scale;
            obstacle.layer = layer;
            obstacle.GetComponent<MeshRenderer>().sharedMaterial = material;
        }

        static void SetLayerRecursively(GameObject target, int layer)
        {
            target.layer = layer;
            foreach (Transform child in target.transform)
                SetLayerRecursively(child.gameObject, layer);
        }

        // ---------------------------------------------------------------- serialized helpers

        /// <summary>Writes auto-property backing fields, which is how [field: SerializeField] data is authored.</summary>
        class Fields : Raw
        {
            public Fields(UnityEngine.Object target) : base(target) { }
            protected override string Resolve(string name) => $"<{name}>k__BackingField";
        }

        class Raw : IDisposable
        {
            readonly SerializedObject _serialized;

            public Raw(UnityEngine.Object target) => _serialized = new SerializedObject(target);

            protected virtual string Resolve(string name) => name;

            public Raw Ref(string name, UnityEngine.Object value)
            {
                Find(name).objectReferenceValue = value;
                return this;
            }

            public Raw Num(string name, float value)
            {
                Find(name).floatValue = value;
                return this;
            }

            public Raw Int(string name, int value)
            {
                Find(name).intValue = value;
                return this;
            }

            public Raw Str(string name, string value)
            {
                Find(name).stringValue = value;
                return this;
            }

            public Raw Vec(string name, Vector3 value)
            {
                Find(name).vector3Value = value;
                return this;
            }

            SerializedProperty Find(string name)
            {
                var resolved = Resolve(name);
                var property = _serialized.FindProperty(resolved);
                if (property == null)
                    throw new Exception($"'{resolved}' not found on {_serialized.targetObject.GetType().Name}");

                return property;
            }

            public void Dispose() => _serialized.ApplyModifiedPropertiesWithoutUndo();
        }
    }
}
