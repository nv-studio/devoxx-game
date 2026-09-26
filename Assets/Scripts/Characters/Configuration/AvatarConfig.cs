using DevoxxGame.Core;
using UnityEngine;

namespace DevoxxGame.Characters.Configuration
{
    /// <summary>
    /// Everything that makes one character look and measure differently from another: the model
    /// dropped under Visuals, and the body dimensions the collider and camera target are built from.
    /// </summary>
    [CreateAssetMenu(menuName = "DevoxxGame/Characters/Avatar Config", fileName = "AvatarConfig")]
    public class AvatarConfig : DevoxxScriptableObject
    {
        [field: Header("Model")]
        [field: SerializeField] public GameObject ModelPrefab { get; private set; }
        [field: SerializeField] public Vector3 ModelLocalPosition { get; private set; }
        [field: SerializeField] public float ModelScale { get; private set; } = 1f;

        [field: Header("Body")]
        [field: SerializeField] public float ColliderHeight { get; private set; } = 2f;
        [field: SerializeField] public float ColliderRadius { get; private set; } = 0.5f;
        [field: SerializeField] public float CameraTargetHeight { get; private set; } = 1.5f;
    }
}
