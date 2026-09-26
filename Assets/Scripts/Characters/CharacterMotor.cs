using DevoxxGame.Characters.Configuration;
using UnityEngine;

namespace DevoxxGame.Characters
{
    /// <summary>
    /// Turns a CharacterCommand into Rigidbody motion: omnidirectional ground movement, turn to
    /// face, and jump. Every number comes from the MovementConfig it is handed.
    /// </summary>
    [RequireComponent(typeof(Rigidbody))]
    public class CharacterMotor : MonoBehaviour
    {
        [field: SerializeField] public Rigidbody Body { get; private set; }
        [field: SerializeField] public GroundProbe GroundProbe { get; private set; }

        MovementConfig _config;
        CharacterCommand _command;
        float _jumpBufferRemaining;

        void Awake()
        {
            if (!Body)
                Body = GetComponent<Rigidbody>();
            if (!GroundProbe)
                GroundProbe = GetComponent<GroundProbe>();
        }

        public void Configure(MovementConfig config)
        {
            _config = config;
            GroundProbe.Configure(config);
        }

        public void SetCommand(in CharacterCommand command)
        {
            _command = command;

            if (command.JumpRequested && _config)
                _jumpBufferRemaining = _config.JumpBufferTime;
        }

        void FixedUpdate()
        {
            if (!_config)
                return;

            var deltaTime = Time.fixedDeltaTime;
            ApplyHorizontalMovement(deltaTime);
            ApplyTurn(deltaTime);
            ApplyJump(deltaTime);
            ApplyFallGravity();
        }

        void ApplyHorizontalMovement(float deltaTime)
        {
            var velocity = Body.linearVelocity;
            var horizontal = new Vector3(velocity.x, 0f, velocity.z);
            var target = _command.MoveDirection * _config.MaxSpeed;

            var hasInput = _command.MoveDirection.sqrMagnitude > 0.0001f;
            var rate = hasInput ? _config.Acceleration : _config.Deceleration;
            if (!GroundProbe.IsGrounded)
                rate *= _config.AirAccelerationMultiplier;

            var change = Vector3.MoveTowards(horizontal, target, rate * deltaTime) - horizontal;
            Body.AddForce(change, ForceMode.VelocityChange);
        }

        void ApplyTurn(float deltaTime)
        {
            if (_command.MoveDirection.sqrMagnitude <= 0.0001f)
                return;

            var desired = Quaternion.LookRotation(_command.MoveDirection, Vector3.up);
            Body.MoveRotation(Quaternion.RotateTowards(Body.rotation, desired, _config.TurnSpeed * deltaTime));
        }

        void ApplyJump(float deltaTime)
        {
            _jumpBufferRemaining = Mathf.Max(0f, _jumpBufferRemaining - deltaTime);
            if (_jumpBufferRemaining <= 0f)
                return;

            if (!GroundProbe.IsGrounded && GroundProbe.TimeSinceGrounded > _config.CoyoteTime)
                return;

            _jumpBufferRemaining = 0f;

            var velocity = Body.linearVelocity;
            velocity.y = Mathf.Sqrt(2f * Mathf.Abs(Physics.gravity.y) * _config.JumpHeight);
            Body.linearVelocity = velocity;

            GroundProbe.NotifyJumped();
        }

        void ApplyFallGravity()
        {
            if (Body.linearVelocity.y >= 0f)
                return;

            Body.AddForce(Physics.gravity * (_config.FallGravityMultiplier - 1f), ForceMode.Acceleration);
        }
    }
}
