using DevoxxGame.Characters.Configuration;
using UnityEngine;

namespace DevoxxGame.Characters
{
    /// <summary>
    /// Lives on the Visuals child and owns the swappable model. The rest of the character never
    /// touches the art, so a new avatar is an asset change rather than a prefab change.
    /// </summary>
    public class CharacterVisuals : MonoBehaviour
    {
        GameObject _model;

        public void Configure(AvatarConfig avatar)
        {
            if (_model)
                Destroy(_model);

            if (!avatar || !avatar.ModelPrefab)
                return;

            _model = Instantiate(avatar.ModelPrefab, transform);
            _model.transform.SetLocalPositionAndRotation(avatar.ModelLocalPosition, Quaternion.identity);
            _model.transform.localScale = Vector3.one * avatar.ModelScale;
        }
    }
}
