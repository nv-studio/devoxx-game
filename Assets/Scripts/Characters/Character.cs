using DevoxxGame.Characters.Configuration;
using UnityEngine;

namespace DevoxxGame.Characters
{
    /// <summary>
    /// Root of the Character prefab. One prefab serves every character in the game: it is handed a
    /// CharacterConfig and builds itself from it. It has no idea who is driving it.
    /// </summary>
    [RequireComponent(typeof(Rigidbody))]
    public class Character : MonoBehaviour
    {
        [field: SerializeField] public CharacterMotor Motor { get; private set; }
        [field: SerializeField] public CharacterVisuals Visuals { get; private set; }
        [field: SerializeField] public CapsuleCollider Body { get; private set; }
        [field: SerializeField] public Transform CameraTarget { get; private set; }

        public CharacterConfig Config { get; private set; }

        void Awake()
        {
            if (!Motor)
                Motor = GetComponent<CharacterMotor>();
            if (!Body)
                Body = GetComponent<CapsuleCollider>();
            if (!Visuals)
                Visuals = GetComponentInChildren<CharacterVisuals>(true);
        }

        public void Configure(CharacterConfig config)
        {
            Config = config;
            if (!config)
                return;

            ApplyAvatar(config.Avatar);
            Motor.Configure(config.Movement);
        }

        public void Drive(in CharacterCommand command) => Motor.SetCommand(command);

        void ApplyAvatar(AvatarConfig avatar)
        {
            if (!avatar)
                return;

            Body.height = avatar.ColliderHeight;
            Body.radius = avatar.ColliderRadius;
            Body.center = new Vector3(0f, avatar.ColliderHeight * 0.5f, 0f);

            if (CameraTarget)
                CameraTarget.localPosition = new Vector3(0f, avatar.CameraTargetHeight, 0f);

            Visuals.Configure(avatar);
        }
    }
}
