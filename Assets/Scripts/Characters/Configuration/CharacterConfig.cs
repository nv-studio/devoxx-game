using DevoxxGame.Core;
using UnityEngine;

namespace DevoxxGame.Characters.Configuration
{
    /// <summary>
    /// The avatar configuration a Character prefab instance is handed to become a specific character.
    /// </summary>
    [CreateAssetMenu(menuName = "DevoxxGame/Characters/Character Config", fileName = "CharacterConfig")]
    public class CharacterConfig : DevoxxScriptableObject
    {
        [field: SerializeField] public AvatarConfig Avatar { get; private set; }
        [field: SerializeField] public MovementConfig Movement { get; private set; }
    }
}
