using DevoxxGame.Characters;
using UnityEngine;

namespace DevoxxGame.Players
{
    /// <summary>
    /// Drives one character on behalf of a local player. Possession is deliberately runtime state:
    /// switching characters, or adding a second player, means another brain rather than another
    /// character prefab.
    /// </summary>
    public class PlayerBrain : MonoBehaviour
    {
        [field: SerializeField] public PlayerInputReader InputReader { get; private set; }
        [field: SerializeField] public PlayerCameraRig CameraRig { get; private set; }
        [field: SerializeField] public CharacterSpawner Spawner { get; private set; }

        public Character Possessed { get; private set; }

        void Awake()
        {
            if (!InputReader)
                InputReader = GetComponent<PlayerInputReader>();
            if (!CameraRig)
                CameraRig = GetComponentInChildren<PlayerCameraRig>(true);
            if (!Spawner)
                Spawner = GetComponent<CharacterSpawner>();
        }

        void Start()
        {
            if (!Spawner)
                return;

            var character = Spawner.Spawn();
            if (character)
                Possess(character);
        }

        public void Possess(Character character)
        {
            if (Possessed)
                Release();

            Possessed = character;
            CameraRig.SetTarget(character ? character.CameraTarget : null);
        }

        public void Release()
        {
            if (Possessed)
                Possessed.Drive(default);

            Possessed = null;
            CameraRig.SetTarget(null);
        }

        void Update()
        {
            if (!Possessed)
                return;

            Possessed.Drive(new CharacterCommand(ToWorldDirection(InputReader.Move), InputReader.ConsumeJump()));
        }

        /// <summary>
        /// Projects stick/WASD input onto the camera's yaw plane. The character is handed world
        /// space so it never needs to know a camera exists.
        /// </summary>
        Vector3 ToWorldDirection(Vector2 input)
        {
            if (input.sqrMagnitude < 0.0001f || !CameraRig || !CameraRig.YawReference)
                return Vector3.zero;

            var reference = CameraRig.YawReference;
            var forward = Vector3.ProjectOnPlane(reference.forward, Vector3.up);
            if (forward.sqrMagnitude < 0.0001f)
                forward = Vector3.ProjectOnPlane(reference.up, Vector3.up);

            forward.Normalize();
            var right = Vector3.Cross(Vector3.up, forward);

            return Vector3.ClampMagnitude(right * input.x + forward * input.y, 1f);
        }
    }
}
