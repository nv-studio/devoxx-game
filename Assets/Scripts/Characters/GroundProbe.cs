using DevoxxGame.Characters.Configuration;
using UnityEngine;

namespace DevoxxGame.Characters
{
    /// <summary>
    /// Spherecasts down from the character's feet to answer "am I standing on something walkable".
    /// </summary>
    public class GroundProbe : MonoBehaviour
    {
        const float SkinWidth = 0.05f;
        const float PostJumpSuppression = 0.1f;

        [field: SerializeField] public Transform Origin { get; private set; }

        MovementConfig _config;
        float _suppressedUntil;

        public bool IsGrounded { get; private set; }
        public Vector3 GroundNormal { get; private set; } = Vector3.up;
        public float TimeSinceGrounded { get; private set; } = float.MaxValue;

        void Awake()
        {
            if (!Origin)
                Origin = transform;
        }

        public void Configure(MovementConfig config) => _config = config;

        /// <summary>
        /// Blanks the probe briefly after a jump, so the frame spent still overlapping the floor
        /// does not hand out a second jump.
        /// </summary>
        public void NotifyJumped()
        {
            _suppressedUntil = Time.time + PostJumpSuppression;
            IsGrounded = false;
            TimeSinceGrounded = float.MaxValue;
        }

        void FixedUpdate()
        {
            if (!_config)
                return;

            var normal = Vector3.up;
            IsGrounded = Time.time >= _suppressedUntil && Probe(out normal);
            GroundNormal = IsGrounded ? normal : Vector3.up;
            TimeSinceGrounded = IsGrounded ? 0f : TimeSinceGrounded + Time.fixedDeltaTime;
        }

        bool Probe(out Vector3 normal)
        {
            normal = Vector3.up;

            var start = Origin.position + Vector3.up * (_config.GroundProbeRadius + SkinWidth);
            if (!Physics.SphereCast(
                    start,
                    _config.GroundProbeRadius,
                    Vector3.down,
                    out var hit,
                    _config.GroundProbeDistance + SkinWidth,
                    _config.GroundLayers,
                    QueryTriggerInteraction.Ignore))
                return false;

            normal = hit.normal;
            return Vector3.Angle(hit.normal, Vector3.up) <= _config.MaxSlopeAngle;
        }

        void OnDrawGizmosSelected()
        {
            if (!_config)
                return;

            var origin = Origin ? Origin : transform;
            var start = origin.position + Vector3.up * (_config.GroundProbeRadius + SkinWidth);
            var end = start + Vector3.down * (_config.GroundProbeDistance + SkinWidth);

            Gizmos.color = IsGrounded ? Color.green : Color.red;
            Gizmos.DrawWireSphere(end, _config.GroundProbeRadius);
            Gizmos.DrawLine(start, end);
        }
    }
}
