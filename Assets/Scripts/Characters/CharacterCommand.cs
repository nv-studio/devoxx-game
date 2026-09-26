using UnityEngine;

namespace DevoxxGame.Characters
{
    /// <summary>
    /// One frame of intent, in world space. This is the whole contract between whatever is driving
    /// a character (a player brain today, an AI or network brain later) and the character itself,
    /// which is why the direction is already resolved to world space and carries no camera.
    /// </summary>
    public readonly struct CharacterCommand
    {
        /// <summary>Desired horizontal heading, XZ only, magnitude 0..1.</summary>
        public Vector3 MoveDirection { get; }

        public bool JumpRequested { get; }

        public CharacterCommand(Vector3 moveDirection, bool jumpRequested)
        {
            MoveDirection = moveDirection;
            JumpRequested = jumpRequested;
        }
    }
}
