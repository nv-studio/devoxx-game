using DevoxxGame.Core;
using UnityEngine;

namespace DevoxxGame.Characters.Configuration
{
    /// <summary>
    /// Locomotion tuning. Shared freely between characters of different shapes.
    /// </summary>
    [CreateAssetMenu(menuName = "DevoxxGame/Characters/Movement Config", fileName = "MovementConfig")]
    public class MovementConfig : DevoxxScriptableObject
    {
        [field: Header("Ground movement")]
        [field: SerializeField] public float MaxSpeed { get; private set; } = 6f;
        [field: SerializeField] public float Acceleration { get; private set; } = 40f;
        [field: SerializeField] public float Deceleration { get; private set; } = 60f;
        [field: SerializeField] public float TurnSpeed { get; private set; } = 720f;

        [field: Header("Air movement")]
        [field: SerializeField]
        [field: Range(0f, 1f)]
        public float AirAccelerationMultiplier { get; private set; } = 0.4f;

        [field: SerializeField] public float JumpHeight { get; private set; } = 1.5f;
        [field: SerializeField] public float FallGravityMultiplier { get; private set; } = 2f;
        [field: SerializeField] public float CoyoteTime { get; private set; } = 0.12f;
        [field: SerializeField] public float JumpBufferTime { get; private set; } = 0.12f;

        [field: Header("Ground probe")]
        [field: SerializeField] public float GroundProbeRadius { get; private set; } = 0.4f;
        [field: SerializeField] public float GroundProbeDistance { get; private set; } = 0.25f;
        [field: SerializeField] public LayerMask GroundLayers { get; private set; }

        [field: SerializeField]
        [field: Range(0f, 89f)]
        public float MaxSlopeAngle { get; private set; } = 50f;
    }
}
