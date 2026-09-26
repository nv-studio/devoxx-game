using UnityEngine;

namespace DevoxxGame.Core
{
    /// <summary>
    /// Base type for every ScriptableObject in the project. Config assets are authored in the
    /// inspector and treated as immutable once play mode starts.
    /// </summary>
    public abstract class DevoxxScriptableObject : ScriptableObject
    {
        [field: SerializeField] public string DisplayName { get; private set; }

        [field: SerializeField]
        [field: TextArea(2, 6)]
        public string DeveloperNotes { get; private set; }

        protected virtual void OnValidate()
        {
            if (string.IsNullOrWhiteSpace(DisplayName))
                DisplayName = name;
        }
    }
}
