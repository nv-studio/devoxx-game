using UnityEngine;
using UnityEngine.InputSystem;

namespace DevoxxGame.Players
{
    /// <summary>
    /// The only place the project reads device input. It reads; it does not move anything.
    /// </summary>
    public class PlayerInputReader : MonoBehaviour
    {
        [field: SerializeField] public PlayerInput Source { get; private set; }

        InputAction _move;
        InputAction _jump;
        bool _jumpQueued;

        public Vector2 Move => _move != null ? _move.ReadValue<Vector2>() : Vector2.zero;

        void OnEnable()
        {
            if (!Source)
                Source = GetComponent<PlayerInput>();

            _move = Source.actions.FindAction("Move", true);
            _jump = Source.actions.FindAction("Jump", true);
            _jump.performed += OnJumpPerformed;
        }

        void OnDisable()
        {
            if (_jump != null)
                _jump.performed -= OnJumpPerformed;

            _jumpQueued = false;
        }

        /// <summary>Returns true once per jump press, so a press between fixed steps is not lost.</summary>
        public bool ConsumeJump()
        {
            if (!_jumpQueued)
                return false;

            _jumpQueued = false;
            return true;
        }

        void OnJumpPerformed(InputAction.CallbackContext context) => _jumpQueued = true;
    }
}
