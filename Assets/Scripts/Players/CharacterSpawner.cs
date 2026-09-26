using DevoxxGame.Characters;
using DevoxxGame.Characters.Configuration;
using UnityEngine;

namespace DevoxxGame.Players
{
    /// <summary>
    /// Spawns a configured character at its own transform, so the rig's position in the scene is
    /// the spawn point and no cross-object scene reference is needed.
    /// </summary>
    public class CharacterSpawner : MonoBehaviour
    {
        [field: SerializeField] public Character CharacterPrefab { get; private set; }
        [field: SerializeField] public CharacterConfig Config { get; private set; }

        public Character Spawn() => Spawn(Config);

        public Character Spawn(CharacterConfig config)
        {
            if (!CharacterPrefab)
            {
                Debug.LogError($"{nameof(CharacterSpawner)} on '{name}' has no character prefab assigned.", this);
                return null;
            }

            var character = Instantiate(CharacterPrefab, transform.position, transform.rotation);
            character.Configure(config);
            return character;
        }
    }
}
